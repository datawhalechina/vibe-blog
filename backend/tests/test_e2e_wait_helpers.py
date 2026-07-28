from unittest.mock import MagicMock

import pytest

from tests import e2e_utils


class FakePage:
    def __init__(self, *, outline=None, event_types=None):
        self.outline = outline
        self.event_types = event_types or []
        self.waits = []

    def evaluate(self, expression):
        if "__sse_outline_data" in expression:
            return self.outline
        if "__sse_events" in expression:
            return self.event_types
        return None

    def wait_for_timeout(self, milliseconds):
        self.waits.append(milliseconds)


def test_sse_hook_captures_interactive_outline_ready_event():
    assert "type === 'outline_ready'" in e2e_utils.SSE_HOOK_JS
    assert "window.__sse_outline_data = d" in e2e_utils.SSE_HOOK_JS


def test_wait_for_generation_requires_terminal_task_and_readable_history(monkeypatch):
    page = FakePage(event_types=["result", "complete"])
    task_states = iter([
        {"status": "running", "current_stage": "writer"},
        {"status": "completed", "current_stage": "done"},
    ])
    history = iter([
        {"success": True, "id": "task-1"},
        {"success": True, "id": "task-1"},
    ])
    monkeypatch.setattr(e2e_utils, "get_task_status", lambda _task_id: next(task_states))
    monkeypatch.setattr(e2e_utils, "get_blog_detail_api", lambda _task_id: next(history))

    result = e2e_utils.wait_for_generation_history(
        page, "task-1", max_wait=5, poll_interval=1
    )

    assert result["blog_id"] == "task-1"
    assert result["blog"]["success"] is True
    assert result["task"]["status"] == "completed"
    assert page.waits == [1000]


def test_wait_for_generation_stops_on_terminal_failure(monkeypatch):
    page = FakePage(event_types=["error"])
    monkeypatch.setattr(
        e2e_utils,
        "get_task_status",
        lambda _task_id: {
            "status": "failed",
            "current_stage": "researcher",
            "error": "provider timeout",
        },
    )
    monkeypatch.setattr(e2e_utils, "get_blog_detail_api", MagicMock(return_value=None))

    with pytest.raises(AssertionError, match="provider timeout"):
        e2e_utils.wait_for_generation_history(page, "task-1", max_wait=5)

    assert page.waits == []


def test_wait_for_generation_limits_completed_history_grace(monkeypatch):
    page = FakePage(event_types=["complete"])
    monkeypatch.setattr(
        e2e_utils,
        "get_task_status",
        lambda _task_id: {"status": "completed", "current_stage": "done"},
    )
    monkeypatch.setattr(e2e_utils, "get_blog_detail_api", MagicMock(return_value=None))

    with pytest.raises(AssertionError, match="已完成但历史仍不可读"):
        e2e_utils.wait_for_generation_history(
            page,
            "task-1",
            max_wait=600,
            poll_interval=1,
            completed_history_grace=2,
        )

    assert page.waits == [1000, 1000]


def test_wait_for_outline_returns_captured_sse_data(monkeypatch):
    outline = {"title": "Test", "sections": [{"title": "One"}]}
    page = FakePage(outline=outline, event_types=["result"])
    monkeypatch.setattr(e2e_utils, "get_task_status", MagicMock())

    assert e2e_utils.wait_for_outline(page, "task-1", max_wait=5) == outline


def test_wait_for_outline_reports_terminal_task_state(monkeypatch):
    page = FakePage(event_types=["progress", "error"])
    monkeypatch.setattr(
        e2e_utils,
        "get_task_status",
        lambda _task_id: {
            "status": "cancelled",
            "current_stage": "planner",
            "message": "cancelled by user",
        },
    )

    with pytest.raises(AssertionError, match="cancelled by user"):
        e2e_utils.wait_for_outline(page, "task-1", max_wait=5)

    assert page.waits == []
