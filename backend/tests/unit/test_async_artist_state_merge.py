import threading
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from services.blog_generator.generator import BlogGenerator


def _generator_shell():
    generator = BlogGenerator.__new__(BlogGenerator)
    generator._image_tasks = {}
    generator._image_tasks_lock = threading.Lock()
    generator.tracker = MagicMock()
    return generator


def test_coder_and_artist_preprocesses_before_submitting_detached_snapshot():
    generator = _generator_shell()
    generator.coder = MagicMock()
    generator.coder.run.side_effect = lambda state: state
    generator.artist = MagicMock()
    generator.artist.preprocess_ascii_flowcharts.return_value = [
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

    with patch(
        "services.blog_generator.generator.ThreadPoolExecutor",
        return_value=executor,
    ):
        result = generator._coder_and_artist_node(state)

    submitted_state = executor.submit.call_args.args[1]
    assert result["sections"][0]["content"] == "[IMAGE: converted ASCII]"
    assert submitted_state is not result
    assert submitted_state["sections"] is not result["sections"]


def test_wait_for_images_merges_image_ids_without_overwriting_newer_content():
    generator = _generator_shell()
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
    generator._image_tasks["task_1"] = (future, executor)
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

    result = generator._wait_for_images_node(state)

    assert result["sections"][0]["content"] == "newer reviewed content"
    assert result["sections"][0]["image_ids"] == ["existing", "image_1"]
    assert result["images"][0]["id"] == "image_1"
    executor.shutdown.assert_called_once_with(wait=False)
