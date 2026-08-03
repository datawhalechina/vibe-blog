from unittest.mock import MagicMock, call

import pytest


def _run_stream(**kwargs):
    from services.blog_generator.lifecycle.generation_stream import (
        run_generation_stream,
    )

    defaults = {
        "app": MagicMock(),
        "stream_input": {"topic": "Topic"},
        "config": {"configurable": {"thread_id": "blog_task-1"}},
        "task_manager": MagicMock(),
        "task_id": "task-1",
        "interactive": False,
        "initial_generation": True,
        "get_token_usage_fn": MagicMock(return_value=None),
        "project_event_fn": MagicMock(
            side_effect=lambda **values: values["completed_sections"]
        ),
        "update_queue_progress_fn": MagicMock(),
        "on_cancel": None,
    }
    defaults.update(kwargs)
    return run_generation_stream(**defaults), defaults


def test_stream_projects_nodes_in_order_and_threads_section_progress():
    app = MagicMock()
    stream_input = {"topic": "Topic"}
    config = {"configurable": {"thread_id": "blog_task-1"}}
    planner_state = {"outline": {"title": "Plan"}}
    writer_state = {"sections": [{"title": "One"}]}
    app.stream.return_value = [
        {"planner": planner_state},
        {"writer": writer_state},
    ]
    get_token_usage = MagicMock(side_effect=[{"total": 1}, {"total": 2}])
    project_event = MagicMock(side_effect=[0, 1])
    update_queue = MagicMock()
    task_manager = MagicMock()
    task_manager.is_cancelled.return_value = False

    result, _ = _run_stream(
        app=app,
        stream_input=stream_input,
        config=config,
        task_manager=task_manager,
        interactive=True,
        get_token_usage_fn=get_token_usage,
        project_event_fn=project_event,
        update_queue_progress_fn=update_queue,
    )

    app.stream.assert_called_once_with(stream_input, config)
    assert result.cancelled is False
    assert result.completed_sections == 1
    assert project_event.call_args_list == [
        call(
            task_manager=task_manager,
            task_id="task-1",
            node_name="planner",
            state=planner_state,
            completed_sections=0,
            interactive=True,
            token_usage={"total": 1},
            initial_generation=True,
            update_queue_progress_fn=update_queue,
        ),
        call(
            task_manager=task_manager,
            task_id="task-1",
            node_name="writer",
            state=writer_state,
            completed_sections=0,
            interactive=True,
            token_usage={"total": 2},
            initial_generation=True,
            update_queue_progress_fn=update_queue,
        ),
    ]
    assert get_token_usage.call_count == 2


def test_stream_passes_resume_projection_mode():
    app = MagicMock()
    state = {"sections": [{"title": "One"}]}
    app.stream.return_value = [{"writer": state}]
    task_manager = MagicMock()
    task_manager.is_cancelled.return_value = False
    project_event = MagicMock(return_value=1)

    result, _ = _run_stream(
        app=app,
        task_manager=task_manager,
        initial_generation=False,
        project_event_fn=project_event,
    )

    assert result.completed_sections == 1
    assert project_event.call_args.kwargs["initial_generation"] is False


def test_stream_cancellation_stops_before_projection_and_runs_callback():
    app = MagicMock()
    app.stream.return_value = [{"writer": {"sections": []}}]
    task_manager = MagicMock()
    task_manager.is_cancelled.return_value = True
    project_event = MagicMock()
    get_token_usage = MagicMock()
    on_cancel = MagicMock()

    result, _ = _run_stream(
        app=app,
        task_manager=task_manager,
        project_event_fn=project_event,
        get_token_usage_fn=get_token_usage,
        on_cancel=on_cancel,
    )

    assert result.cancelled is True
    assert result.completed_sections == 0
    on_cancel.assert_called_once_with()
    project_event.assert_not_called()
    get_token_usage.assert_not_called()
    task_manager.send_event.assert_called_once_with(
        "task-1",
        "cancelled",
        {"task_id": "task-1", "message": "任务已被用户取消"},
    )


def test_stream_cancellation_does_not_require_callback():
    app = MagicMock()
    app.stream.return_value = [{"planner": {}}]
    task_manager = MagicMock()
    task_manager.is_cancelled.return_value = True

    result, _ = _run_stream(app=app, task_manager=task_manager, on_cancel=None)

    assert result.cancelled is True


def test_stream_without_task_manager_skips_token_lookup_but_still_delegates():
    app = MagicMock()
    state = {"outline": {"title": "Plan"}}
    app.stream.return_value = [{"planner": state}]
    get_token_usage = MagicMock()
    project_event = MagicMock(return_value=0)

    result, _ = _run_stream(
        app=app,
        task_manager=None,
        get_token_usage_fn=get_token_usage,
        project_event_fn=project_event,
    )

    assert result.cancelled is False
    get_token_usage.assert_not_called()
    assert project_event.call_args.kwargs["task_manager"] is None
    assert project_event.call_args.kwargs["token_usage"] is None


def test_stream_does_not_swallow_graph_errors():
    app = MagicMock()
    app.stream.side_effect = RuntimeError("graph failed")

    with pytest.raises(RuntimeError, match="graph failed"):
        _run_stream(app=app)
