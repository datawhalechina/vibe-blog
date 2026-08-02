import inspect
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.blog_generator.orchestrator.image_task_registry import ImageTaskRegistry
from services.blog_generator.orchestrator.nodes.finalization import (
    assembler_node,
    coder_and_artist_node,
    factcheck_node,
    humanizer_node,
    merge_artist_image_ids,
    summary_generator_node,
    text_cleanup_node,
    wait_for_images_node,
)


FINALIZATION_NODES = (
    coder_and_artist_node,
    wait_for_images_node,
    factcheck_node,
    text_cleanup_node,
    humanizer_node,
    assembler_node,
    summary_generator_node,
)


def test_finalization_nodes_use_explicit_keyword_dependencies():
    for node in FINALIZATION_NODES:
        parameters = inspect.signature(node).parameters
        assert "generator" not in parameters
        assert "context" not in parameters
        assert list(parameters)[0] == "state"
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in list(parameters.values())[1:]
        )


def test_coder_and_artist_registers_detached_artist_snapshot():
    coder = MagicMock()
    coder.run.side_effect = lambda state: state
    artist = MagicMock()
    artist.preprocess_ascii_flowcharts.return_value = [
        {"id": "one", "content": "converted"}
    ]
    executor = MagicMock()
    future = Future()
    executor.submit.return_value = future
    registry = MagicMock()
    state = {"sections": [{"id": "one", "content": "ascii"}], "code_blocks": []}

    result = coder_and_artist_node(
        state,
        coder=coder,
        artist=artist,
        image_task_registry=registry,
        executor_factory=MagicMock(return_value=executor),
        uuid_factory=MagicMock(return_value="task-1"),
    )

    submitted_state = executor.submit.call_args.args[1]
    assert result["_image_task_id"] == "task-1"
    assert submitted_state is not result
    assert submitted_state["sections"] is not result["sections"]
    registry.register.assert_called_once_with("task-1", future, executor)


def test_wait_for_images_merges_images_without_overwriting_reviewed_content():
    registry = ImageTaskRegistry()
    future = Future()
    future.set_result({
        "sections": [
            {"id": "one", "content": "old", "image_ids": ["image-1"]}
        ],
        "images": [{"id": "image-1", "render_method": "mermaid"}],
        "section_images": ["https://example.com/section.png"],
    })
    executor = MagicMock()
    registry.register("task-1", future, executor)
    tracker = MagicMock()
    state = {
        "_image_task_id": "task-1",
        "sections": [{"id": "one", "content": "reviewed", "image_ids": []}],
        "images": [],
    }

    result = wait_for_images_node(
        state,
        image_task_registry=registry,
        tracker=tracker,
        timeout=600,
    )

    assert result["sections"][0]["content"] == "reviewed"
    assert result["sections"][0]["image_ids"] == ["image-1"]
    assert result["section_images"] == ["https://example.com/section.png"]
    tracker.log_image_generation.assert_called_once()
    executor.shutdown.assert_called_once_with(wait=False)


def test_merge_artist_image_ids_deduplicates_and_preserves_order():
    current = [{"id": "one", "image_ids": ["existing"]}]
    merge_artist_image_ids(
        current,
        [{"id": "one", "image_ids": ["existing", "new"]}],
    )
    assert current[0]["image_ids"] == ["existing", "new"]


def test_factcheck_mini_skips_optional_agent():
    factcheck = MagicMock()
    state = {"target_length": "mini"}
    assert factcheck_node(
        state,
        factcheck=factcheck,
        configured_style=None,
        env_factcheck=True,
    ) is state
    factcheck.run.assert_not_called()


def test_text_cleanup_uses_injected_cleanup_function():
    cleanup = MagicMock(return_value={"text": "clean", "total_fixes": 1, "stats": {}})
    state = {"sections": [{"title": "One", "content": "dirty"}]}
    result = text_cleanup_node(
        state,
        cleanup=cleanup,
        configured_style=SimpleNamespace(enable_text_cleanup=True),
        env_text_cleanup=True,
    )
    assert result["sections"][0]["content"] == "clean"
