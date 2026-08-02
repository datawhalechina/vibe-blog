from concurrent.futures import Future
from unittest.mock import MagicMock

from services.blog_generator.orchestrator.image_task_registry import ImageTaskRegistry
from services.blog_generator.orchestrator.nodes.finalization import (
    coder_and_artist_node,
    wait_for_images_node,
)


def test_coder_and_artist_preprocesses_before_submitting_detached_snapshot():
    coder = MagicMock()
    coder.run.side_effect = lambda state: state
    artist = MagicMock()
    artist.preprocess_ascii_flowcharts.return_value = [
        {
            "id": "intro",
            "title": "Intro",
            "content": "[IMAGE: converted ASCII]",
        }
    ]
    executor = MagicMock()
    executor.submit.return_value = Future()
    state = {
        "sections": [{"id": "intro", "title": "Intro", "content": "ASCII"}],
        "code_blocks": [],
    }

    result = coder_and_artist_node(
        state,
        coder=coder,
        artist=artist,
        image_task_registry=MagicMock(),
        executor_factory=MagicMock(return_value=executor),
        uuid_factory=MagicMock(return_value="task_1"),
    )

    submitted_state = executor.submit.call_args.args[1]
    assert result["sections"][0]["content"] == "[IMAGE: converted ASCII]"
    assert submitted_state is not result
    assert submitted_state["sections"] is not result["sections"]


def test_wait_for_images_merges_image_ids_without_overwriting_newer_content():
    registry = ImageTaskRegistry()
    future = Future()
    future.set_result(
        {
            "sections": [
                {
                    "id": "intro",
                    "title": "Intro",
                    "content": "older content",
                    "image_ids": ["image_1"],
                }
            ],
            "images": [
                {
                    "id": "image_1",
                    "render_method": "mermaid",
                    "content": "flowchart TD",
                    "caption": "Flow",
                }
            ],
        }
    )
    executor = MagicMock()
    registry.register("task_1", future, executor)
    state = {
        "_image_task_id": "task_1",
        "sections": [
            {
                "id": "intro",
                "title": "Intro",
                "content": "newer reviewed content",
                "image_ids": ["existing"],
            }
        ],
        "images": [],
    }

    result = wait_for_images_node(
        state,
        image_task_registry=registry,
        tracker=MagicMock(),
        timeout=600,
    )

    assert result["sections"][0]["content"] == "newer reviewed content"
    assert result["sections"][0]["image_ids"] == ["existing", "image_1"]
    assert result["images"][0]["id"] == "image_1"
    executor.shutdown.assert_called_once_with(wait=False)
