from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.blog_generator.blog_service import BlogService


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
