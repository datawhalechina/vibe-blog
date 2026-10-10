"""Task-scoped SSE logging must not mix concurrent generation progress."""

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest

from logging_config import task_id_context
from services.blog_generator.lifecycle.task_events import TaskEventBridge
from services.task_service import TaskManager


@pytest.fixture
def task_streams(monkeypatch):
    # Exercise real queues without retaining the process-wide singleton across tests.
    monkeypatch.setattr(TaskManager, "_instance", None)
    manager = TaskManager()
    bridges = {}
    for task_id in ("task-a", "task-b"):
        manager.create_task(task_id)
        bridges[task_id] = TaskEventBridge(None, manager, task_id)
        bridges[task_id].attach()

    logger = logging.getLogger("services.blog_generator.agents.researcher")
    monkeypatch.setattr(logger, "level", logging.INFO)
    token = task_id_context.set("")
    try:
        yield manager, bridges, logger
    finally:
        task_id_context.reset(token)
        for bridge in bridges.values():
            bridge.close()


def _emit(logger, task_id, message, **kwargs):
    token = task_id_context.set(task_id)
    try:
        logger.info(message, **kwargs)
    finally:
        task_id_context.reset(token)


def _drain(manager, task_id):
    queue = manager.get_queue(task_id)
    events = []
    while not queue.empty():
        payload = queue.get_nowait()
        events.append((payload["event"], payload["data"]))
    return events


@pytest.mark.parametrize("concurrent", [False, True])
def test_routes_logs_and_search_events_only_to_the_originating_task(task_streams, concurrent):
    manager, _, logger = task_streams
    barrier = Barrier(2) if concurrent else None

    def emit_search(task_id):
        token = task_id_context.set(task_id)
        try:
            if barrier:
                barrier.wait(timeout=5)
            logger.info("Web Search 搜索: %s-only-query", task_id)
        finally:
            task_id_context.reset(token)

    if concurrent:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(emit_search, ("task-a", "task-b")))
    else:
        emit_search("task-a")
        emit_search("task-b")

    for task_id in ("task-a", "task-b"):
        query = f"{task_id}-only-query"
        assert _drain(manager, task_id) == [
            ("log", {
                "level": "INFO", "logger": "researcher",
                "message": f"Web Search 搜索: {query}",
            }),
            ("result", {"type": "search_started", "data": {"query": query}}),
        ]


@pytest.mark.parametrize("display_task_id", [None, "", "[task-a]", "[task-b]"])
def test_task_context_is_authoritative_before_record_formatting(task_streams, display_task_id):
    manager, _, logger = task_streams
    extra = {} if display_task_id is None else {"task_id": display_task_id}
    _emit(logger, "task-a", "Research completed", extra=extra)

    assert len(_drain(manager, "task-a")) == 1
    assert _drain(manager, "task-b") == []


@pytest.mark.parametrize("display_task_id", [None, "[task-a]"])
def test_unscoped_logs_are_not_broadcast(task_streams, display_task_id):
    manager, _, logger = task_streams
    extra = {} if display_task_id is None else {"task_id": display_task_id}
    logger.info("Web Search 搜索: unscoped-query", extra=extra)

    assert _drain(manager, "task-a") == []
    assert _drain(manager, "task-b") == []


def test_closing_one_bridge_keeps_the_other_task_isolated(task_streams):
    manager, bridges, logger = task_streams
    bridges["task-a"].close()
    bridges["task-a"].close()
    _emit(logger, "task-a", "Closed task")
    _emit(logger, "task-b", "Still running")

    assert _drain(manager, "task-a") == []
    assert [data["message"] for _, data in _drain(manager, "task-b")] == ["Still running"]


def test_missing_queue_still_detaches_its_handler(task_streams):
    manager, bridges, logger = task_streams
    stale_handler = bridges["task-a"].handler
    manager.queues.pop("task-a")
    _emit(logger, "task-a", "Removed queue")

    assert stale_handler not in logger.handlers
    _emit(logger, "task-b", "Remaining task")
    assert [data["message"] for _, data in _drain(manager, "task-b")] == ["Remaining task"]


def test_generate_async_keeps_task_context_in_real_background_threads(task_streams, monkeypatch):
    from services.blog_generator.blog_service import BlogService

    manager, _, logger = task_streams
    service = BlogService.__new__(BlogService)
    barrier = Barrier(2)
    finished = {task_id: Event() for task_id in ("task-a", "task-b")}
    observed_context = {}

    def generate_without_llm(*, task_id, **kwargs):
        try:
            observed_context[task_id] = task_id_context.get()
            barrier.wait(timeout=5)
            logger.info("Generating %s", task_id)
        finally:
            finished[task_id].set()

    monkeypatch.setattr(service, "_run_generation", generate_without_llm)
    for task_id in finished:
        service.generate_async(task_id=task_id, topic="Offline topic", task_manager=manager)
    for done in finished.values():
        assert done.wait(timeout=5)

    assert observed_context == {"task-a": "task-a", "task-b": "task-b"}
    assert task_id_context.get() == ""
    for task_id in finished:
        assert [data["message"] for _, data in _drain(manager, task_id)] == [f"Generating {task_id}"]
