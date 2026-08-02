from concurrent.futures import Future, ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from services.blog_generator.orchestrator.image_task_registry import ImageTaskRegistry


def test_pop_unknown_task_returns_none():
    assert ImageTaskRegistry().pop("missing") is None


def test_pop_returns_future_result_and_shuts_down_executor_once():
    registry = ImageTaskRegistry()
    future = Future()
    future.set_result({"images": ["image-1"]})
    executor = MagicMock()
    registry.register("task-1", future, executor)

    assert registry.pop("task-1") == {"images": ["image-1"]}
    assert registry.pop("task-1") is None
    executor.shutdown.assert_called_once_with(wait=False)


def test_pop_propagates_future_exception_and_still_shuts_down_executor():
    registry = ImageTaskRegistry()
    future = Future()
    future.set_exception(RuntimeError("artist failed"))
    executor = MagicMock()
    registry.register("task-1", future, executor)

    with pytest.raises(RuntimeError, match="artist failed"):
        registry.pop("task-1")

    executor.shutdown.assert_called_once_with(wait=False)


def test_pop_forwards_timeout_to_future():
    registry = ImageTaskRegistry()
    future = MagicMock()
    future.result.return_value = {"images": []}
    executor = MagicMock()
    registry.register("task-1", future, executor)

    assert registry.pop("task-1", timeout=600) == {"images": []}
    future.result.assert_called_once_with(timeout=600)


def test_discard_cancels_pending_future_and_shuts_down_once():
    registry = ImageTaskRegistry()
    future = MagicMock()
    executor = MagicMock()
    registry.register("task-1", future, executor)

    registry.discard("task-1")
    registry.discard("task-1")

    future.cancel.assert_called_once_with()
    executor.shutdown.assert_called_once_with(wait=False)


def test_register_and_pop_are_thread_safe_for_independent_tasks():
    registry = ImageTaskRegistry()
    executors = {f"task-{index}": MagicMock() for index in range(20)}
    futures = {}
    for task_id in executors:
        future = Future()
        future.set_result(task_id)
        futures[task_id] = future

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda task_id: registry.register(
                    task_id, futures[task_id], executors[task_id]
                ),
                executors,
            )
        )
        results = list(pool.map(registry.pop, executors))

    assert set(results) == set(executors)
    for executor in executors.values():
        executor.shutdown.assert_called_once_with(wait=False)
