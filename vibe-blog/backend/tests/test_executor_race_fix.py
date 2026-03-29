"""
Tests for ThreadPoolExecutor race condition fix in _execute_parallel().

Key behavioral changes being tested:
1. All future operations complete inside the `with` block
2. Timed-out futures are cancelled via future.cancel()
3. task_completed events are emitted for each finished task
4. Normal execution and exception handling remain correct
"""

import threading
import time
from unittest.mock import MagicMock

import pytest

from services.blog_generator.parallel.executor import (
    ParallelTaskExecutor,
    TaskResult,
    TaskStatus,
)
from services.blog_generator.parallel.config import TaskConfig


@pytest.fixture
def executor():
    """Create a ParallelTaskExecutor with parallel mode forced on."""
    ex = ParallelTaskExecutor(max_workers=4, default_timeout=10)
    ex._use_parallel = True
    return ex


class TestParallelExecutionNormal:
    """Normal parallel execution: all tasks succeed."""

    def test_all_tasks_complete_successfully(self, executor):
        tasks = [
            {"name": "task_a", "fn": lambda: "result_a"},
            {"name": "task_b", "fn": lambda: "result_b"},
            {"name": "task_c", "fn": lambda: "result_c"},
        ]
        results = executor.run_parallel(tasks)

        assert len(results) == 3
        for r in results:
            assert r.status == TaskStatus.COMPLETED
            assert r.result is not None
            assert r.error is None
            assert r.started_at is not None
            assert r.completed_at is not None
            assert r.duration_ms is not None

    def test_results_preserve_task_order(self, executor):
        """Results list order matches input tasks order."""
        tasks = [
            {"name": f"task_{i}", "fn": lambda i=i: f"result_{i}"}
            for i in range(5)
        ]
        results = executor.run_parallel(tasks)

        for i, r in enumerate(results):
            assert r.result == f"result_{i}"
            assert r.task_name == f"task_{i}"


class TestParallelExecutionException:
    """Tasks that raise exceptions are marked FAILED."""

    def test_exception_marks_task_failed(self, executor):
        def failing_fn():
            raise ValueError("something broke")

        tasks = [
            {"name": "good_task", "fn": lambda: "ok"},
            {"name": "bad_task", "fn": failing_fn},
        ]
        results = executor.run_parallel(tasks)

        good = results[0]
        bad = results[1]

        assert good.status == TaskStatus.COMPLETED
        assert good.result == "ok"

        assert bad.status == TaskStatus.FAILED
        assert "something broke" in bad.error
        assert bad.completed_at is not None
        assert bad.duration_ms is not None


class TestParallelExecutionTimeout:
    """Timeout scenario: slow tasks get TIMED_OUT and futures are cancelled."""

    def test_slow_tasks_marked_timed_out(self, executor):
        """Tasks that exceed timeout are marked TIMED_OUT."""
        barrier = threading.Event()

        def slow_fn():
            barrier.wait(timeout=10)
            return "late"

        def fast_fn():
            return "fast"

        tasks = [
            {"name": "fast_task", "fn": fast_fn},
            {"name": "slow_task", "fn": slow_fn},
        ]
        config = TaskConfig(name="timeout_test", timeout_seconds=1)
        results = executor.run_parallel(tasks, config=config)

        # Clean up: unblock the slow task so the thread can exit
        barrier.set()

        fast_result = results[0]
        slow_result = results[1]

        assert fast_result.status == TaskStatus.COMPLETED
        assert fast_result.result == "fast"

        assert slow_result.status == TaskStatus.TIMED_OUT
        assert "超时" in slow_result.error
        assert slow_result.completed_at is not None

    def test_timed_out_futures_are_cancelled(self):
        """
        Key behavioral change: future.cancel() must be called on
        futures whose tasks timed out. With cancel(), queued tasks
        that haven't started yet will NOT execute during shutdown.

        Setup: 1 worker, 3 tasks. First task blocks, second and third
        are queued. After timeout, cancel() prevents queued tasks from
        running.
        """
        ex = ParallelTaskExecutor(max_workers=1, default_timeout=10)
        ex._use_parallel = True

        task_executed = [False, False, False]

        def blocking_fn():
            time.sleep(1.5)
            task_executed[0] = True
            return "done"

        def quick_fn_1():
            task_executed[1] = True
            return "quick1"

        def quick_fn_2():
            task_executed[2] = True
            return "quick2"

        tasks = [
            {"name": "blocking", "fn": blocking_fn},
            {"name": "quick1", "fn": quick_fn_1},
            {"name": "quick2", "fn": quick_fn_2},
        ]
        config = TaskConfig(name="cancel_test", timeout_seconds=0.5)
        results = ex.run_parallel(tasks, config=config)

        # With future.cancel(), queued tasks should NOT have executed
        assert task_executed[1] is False, (
            "Queued task should not execute after cancel()"
        )
        assert task_executed[2] is False, (
            "Queued task should not execute after cancel()"
        )


class TestTaskCompletedEvents:
    """Verify task_completed events are emitted for each finished task."""

    def test_task_completed_events_emitted(self):
        events = []
        executor = ParallelTaskExecutor(
            max_workers=2,
            default_timeout=10,
            on_task_event=lambda e: events.append(e),
        )
        executor._use_parallel = True

        tasks = [
            {"name": "task_a", "fn": lambda: "a"},
            {"name": "task_b", "fn": lambda: "b"},
        ]
        executor.run_parallel(tasks)

        # Should have: batch_started + 2x task_completed + batch_completed
        event_types = [e["type"] for e in events]
        assert event_types.count("task_completed") == 2
        assert "batch_started" in event_types
        assert "batch_completed" in event_types

    def test_task_completed_event_for_failed_task(self):
        events = []
        executor = ParallelTaskExecutor(
            max_workers=2,
            default_timeout=10,
            on_task_event=lambda e: events.append(e),
        )
        executor._use_parallel = True

        def failing():
            raise RuntimeError("boom")

        tasks = [
            {"name": "ok_task", "fn": lambda: "ok"},
            {"name": "fail_task", "fn": failing},
        ]
        executor.run_parallel(tasks)

        task_events = [e for e in events if e["type"] == "task_completed"]
        assert len(task_events) == 2

        statuses = {e["status"] for e in task_events}
        assert "completed" in statuses
        assert "failed" in statuses
