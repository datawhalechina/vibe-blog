from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.blog_generator.blog_service import BlogService
from services.blog_generator.lifecycle.result_pipeline import GenerationResultPipeline


def test_completion_event_contains_persisted_blog_payload():
    service = BlogService.__new__(BlogService)
    service.generator = SimpleNamespace()
    task_manager = MagicMock()
    final_state = {
        "outline": {"title": "Persisted"},
        "sections": [{"title": "One"}],
        "images": [],
        "code_blocks": [],
        "review_score": 92,
    }

    with (
        patch.object(service, "_get_token_usage", return_value={"total": 12}),
        patch(
            "services.blog_generator.blog_service.update_queue_status"
        ) as update_queue_status,
    ):
        service._send_completion_event(
            task_manager=task_manager,
            task_id="task-1",
            final_state=final_state,
            markdown="# Persisted",
            saved_path="/tmp/persisted.md",
            cover_video_path=None,
            citations=[{"url": "https://example.com"}],
        )

    task_manager.send_event.assert_called_once()
    task_id, event, payload = task_manager.send_event.call_args.args
    assert (task_id, event) == ("task-1", "complete")
    assert payload["id"] == "task-1"
    assert payload["markdown"] == "# Persisted"
    assert payload["sections_count"] == 1
    assert payload["token_usage"] == {"total": 12}
    update_queue_status.assert_called_once_with(
        "task-1", "completed", word_count=11, image_count=0
    )


@pytest.mark.parametrize(
    ("final_state", "message"),
    [
        (
            {"error": "大纲生成失败: LLM 流式调用失败", "final_markdown": ""},
            "大纲生成失败: LLM 流式调用失败",
        ),
        ({"error": None, "final_markdown": "   "}, "博客生成未产生有效内容"),
    ],
)
def test_final_state_validation_rejects_failed_or_empty_generation(
    final_state, message
):
    service = BlogService.__new__(BlogService)

    with pytest.raises(RuntimeError, match=message):
        service._validate_final_state(final_state)


def test_final_state_validation_returns_generated_markdown():
    service = BlogService.__new__(BlogService)

    markdown = service._validate_final_state(
        {"error": None, "final_markdown": "# Generated\n\nBody"}
    )

    assert markdown == "# Generated\n\nBody"


def test_run_generation_reports_failed_state_without_saving_history():
    service = BlogService.__new__(BlogService)
    snapshot = SimpleNamespace(
        next=(),
        tasks=(),
        values={
            "error": "大纲生成失败: LLM 流式调用失败",
            "final_markdown": "# Partial output",
        },
    )
    app = MagicMock()
    app.stream.return_value = []
    app.get_state.return_value = snapshot
    service.generator = SimpleNamespace(
        app=app,
        llm=MagicMock(),
        researcher=SimpleNamespace(search_service=None),
        writer=SimpleNamespace(),
    )
    service._interrupted_tasks = {}
    generate_cover_image = MagicMock()
    service._result_pipeline = GenerationResultPipeline(
        service,
        generate_cover_image_fn=generate_cover_image,
        generate_cover_video_fn=MagicMock(),
    )
    task_manager = MagicMock()
    task_manager.get_queue.return_value = MagicMock()

    with (
        patch.dict(
            "os.environ",
            {
                "TOKEN_TRACKING_ENABLED": "false",
                "BLOG_TASK_LOG_ENABLED": "false",
            },
        ),
        patch("time.sleep"),
        patch("logging_config.create_task_logger", return_value=None),
        patch("services.database_service.get_db_service") as get_db_service,
        patch.object(service, "_save_markdown") as save_markdown,
        patch(
            "services.blog_generator.blog_service.update_queue_status"
        ) as update_queue_status,
    ):
        service._run_generation(
            task_id="task-failed",
            topic="provider failure",
            article_type="tutorial",
            target_audience="developers",
            audience_adaptation="technical-beginner",
            target_length="short",
            source_material="",
            generate_images=True,
            task_manager=task_manager,
        )

    get_db_service.assert_not_called()
    generate_cover_image.assert_not_called()
    save_markdown.assert_not_called()
    event_calls = task_manager.send_event.call_args_list
    assert not any(call.args[1] == "complete" for call in event_calls)
    error_events = [call for call in event_calls if call.args[1] == "error"]
    assert error_events[-1].args[2] == {
        "message": "大纲生成失败: LLM 流式调用失败",
        "recoverable": False,
    }
    update_queue_status.assert_called_once_with(
        "task-failed",
        "failed",
        error_msg="大纲生成失败: LLM 流式调用失败",
    )


def test_run_resume_reports_failed_state_without_saving_history():
    service = BlogService.__new__(BlogService)
    snapshot = SimpleNamespace(
        values={
            "error": "内容生成失败: provider unavailable",
            "final_markdown": "",
        }
    )
    app = MagicMock()
    app.stream.return_value = []
    app.get_state.return_value = snapshot
    service.generator = SimpleNamespace(app=app)
    task_manager = MagicMock()

    with (
        patch("logging_config.create_task_logger", return_value=None),
        patch("services.database_service.get_db_service") as get_db_service,
        patch(
            "services.blog_generator.blog_service.update_queue_status"
        ) as update_queue_status,
    ):
        service._run_resume(
            task_id="task-resume-failed",
            resume_value={"action": "accept"},
            config={"configurable": {"thread_id": "blog-task-resume-failed"}},
            task_manager=task_manager,
            task_info={"generate_images": False, "article_config": {}},
        )

    get_db_service.assert_not_called()
    event_calls = task_manager.send_event.call_args_list
    assert not any(call.args[1] == "complete" for call in event_calls)
    error_events = [call for call in event_calls if call.args[1] == "error"]
    assert error_events[-1].args[2] == {
        "message": "内容生成失败: provider unavailable",
        "recoverable": False,
    }
    update_queue_status.assert_called_once_with(
        "task-resume-failed",
        "failed",
        error_msg="内容生成失败: provider unavailable",
    )
