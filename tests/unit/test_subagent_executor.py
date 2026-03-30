"""
102.01 ParallelTaskExecutor 单元测试
覆盖：并行执行、串行回退、超时保护、异常隔离、SSE 事件、边界条件
"""

import os
import time
import pytest
from unittest.mock import patch
from datetime import datetime


from services.blog_generator.parallel.config import TaskConfig
from services.blog_generator.parallel.executor import (
    ParallelTaskExecutor,
    TaskResult,
    TaskStatus,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def executor():
    return ParallelTaskExecutor(max_workers=3, default_timeout=10)


@pytest.fixture
def serial_executor():
    with patch.dict(os.environ, {"TRACE_ENABLED": "true"}):
        return ParallelTaskExecutor(max_workers=3, default_timeout=10)


@pytest.fixture
def event_collector():
    events = []
    def on_event(event):
        events.append(event)
    return events, on_event


# ============================================================
# 1. 并行执行
# ============================================================

class TestParallelExecution:
    def test_parallel_basic(self, executor):
        """3 个独立任务并行执行，全部成功"""
        def task_fn(value):
            time.sleep(0.05)
            return f"result_{value}"

        tasks = [
            {"name": f"task_{i}", "fn": task_fn, "args": (i,)}
            for i in range(3)
        ]

        start = time.time()
        results = executor.run_parallel(tasks)
        elapsed = time.time() - start

        assert len(results) == 3
        for i, r in enumerate(results):
            assert r.status == TaskStatus.COMPLETED
            assert r.result == f"result_{i}"
            assert r.error is None
            assert r.duration_ms is not None and r.duration_ms > 0

        assert elapsed < 0.3, f"并行执行耗时 {elapsed:.3f}s，预期 < 0.3s"

    def test_parallel_preserves_order(self, executor):
        """结果顺序与输入任务顺序一致"""
        def task_fn(delay, value):
            time.sleep(delay)
            return value

        tasks = [
            {"name": "slow", "fn": task_fn, "args": (0.1, "A")},
            {"name": "fast", "fn": task_fn, "args": (0.01, "B")},
            {"name": "medium", "fn": task_fn, "args": (0.05, "C")},
        ]

        results = executor.run_parallel(tasks)
        assert results[0].result == "A"
        assert results[1].result == "B"
        assert results[2].result == "C"

    def test_parallel_with_kwargs(self, executor):
        def task_fn(prefix="", suffix=""):
            return f"{prefix}_hello_{suffix}"

        tasks = [
            {"name": "t1", "fn": task_fn, "kwargs": {"prefix": "a", "suffix": "z"}},
        ]
        results = executor.run_parallel(tasks)
        assert results[0].result == "a_hello_z"


# ============================================================
# 2. 串行回退
# ============================================================

class TestSerialFallback:
    def test_serial_when_trace_enabled(self, serial_executor):
        call_order = []

        def task_fn(idx):
            call_order.append(idx)
            time.sleep(0.02)
            return idx

        tasks = [
            {"name": f"task_{i}", "fn": task_fn, "args": (i,)}
            for i in range(3)
        ]

        start = time.time()
        results = serial_executor.run_parallel(tasks)
        elapsed = time.time() - start

        assert elapsed >= 0.05
        assert call_order == [0, 1, 2]
        for i, r in enumerate(results):
            assert r.status == TaskStatus.COMPLETED
            assert r.result == i

    def test_single_task_runs_serial(self, executor):
        tasks = [{"name": "only_one", "fn": lambda: "single"}]
        results = executor.run_parallel(tasks)
        assert len(results) == 1
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].result == "single"


# ============================================================
# 3. 超时保护
# ============================================================

class TestTimeoutProtection:
    def test_timeout_marks_timed_out(self):
        executor = ParallelTaskExecutor(max_workers=2, default_timeout=1)

        def slow_task():
            time.sleep(10)
            return "should_not_reach"

        def fast_task():
            return "fast_done"

        tasks = [
            {"name": "slow", "fn": slow_task},
            {"name": "fast", "fn": fast_task},
        ]

        config = TaskConfig(name="timeout_test", timeout_seconds=1)
        results = executor.run_parallel(tasks, config=config)

        fast_result = next(r for r in results if r.task_name == "fast")
        assert fast_result.status == TaskStatus.COMPLETED

        slow_result = next(r for r in results if r.task_name == "slow")
        assert slow_result.status == TaskStatus.TIMED_OUT
        assert "超时" in slow_result.error


# ============================================================
# 4. 异常处理
# ============================================================

class TestErrorHandling:
    def test_exception_isolated(self, executor):
        def good_task():
            return "good"

        def bad_task():
            raise ValueError("模拟异常")

        tasks = [
            {"name": "good_1", "fn": good_task},
            {"name": "bad", "fn": bad_task},
            {"name": "good_2", "fn": good_task},
        ]

        results = executor.run_parallel(tasks)
        assert results[0].status == TaskStatus.COMPLETED
        assert results[1].status == TaskStatus.FAILED
        assert "模拟异常" in results[1].error
        assert results[2].status == TaskStatus.COMPLETED

    def test_all_tasks_fail(self, executor):
        def bad_task(msg):
            raise RuntimeError(msg)

        tasks = [
            {"name": f"bad_{i}", "fn": bad_task, "args": (f"error_{i}",)}
            for i in range(3)
        ]

        results = executor.run_parallel(tasks)
        for i, r in enumerate(results):
            assert r.status == TaskStatus.FAILED
            assert f"error_{i}" in r.error


# ============================================================
# 5. 边界条件
# ============================================================

class TestEdgeCases:
    def test_empty_tasks(self, executor):
        assert executor.run_parallel([]) == []

    def test_task_returns_none(self, executor):
        tasks = [{"name": "none", "fn": lambda: None}]
        results = executor.run_parallel(tasks)
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].result is None

    def test_task_returns_dict(self, executor):
        def dict_task():
            return {"sections": [{"id": "s1", "content": "hello"}]}

        tasks = [{"name": "dict", "fn": dict_task}]
        results = executor.run_parallel(tasks)
        assert results[0].result["sections"][0]["id"] == "s1"

    def test_auto_generated_task_id(self, executor):
        tasks = [{"name": "auto_id", "fn": lambda: "ok"}]
        results = executor.run_parallel(tasks)
        assert results[0].task_id is not None and len(results[0].task_id) > 0

    def test_custom_task_id(self, executor):
        tasks = [{"id": "my-custom-id", "name": "custom", "fn": lambda: "ok"}]
        results = executor.run_parallel(tasks)
        assert results[0].task_id == "my-custom-id"


# ============================================================
# 6. SSE 事件回调
# ============================================================

class TestSSEEvents:
    def test_events_emitted(self, event_collector):
        events, on_event = event_collector
        executor = ParallelTaskExecutor(
            max_workers=2, default_timeout=10, on_task_event=on_event,
        )

        tasks = [
            {"name": f"task_{i}", "fn": lambda: "ok"}
            for i in range(2)
        ]
        executor.run_parallel(tasks)

        event_types = [e["type"] for e in events]
        assert "batch_started" in event_types
        assert event_types.count("task_completed") == 2
        assert "batch_completed" in event_types

    def test_event_callback_exception_ignored(self):
        def bad_callback(event):
            raise RuntimeError("callback error")

        executor = ParallelTaskExecutor(
            max_workers=2, default_timeout=10, on_task_event=bad_callback,
        )
        tasks = [{"name": "t1", "fn": lambda: "ok"}]
        results = executor.run_parallel(tasks)
        assert results[0].status == TaskStatus.COMPLETED


# ============================================================
# 7. TaskResult / TaskConfig
# ============================================================

class TestTaskResult:
    def test_success_property(self):
        assert TaskResult(task_id="1", task_name="t", status=TaskStatus.COMPLETED).success is True
        assert TaskResult(task_id="2", task_name="t", status=TaskStatus.FAILED).success is False
        assert TaskResult(task_id="3", task_name="t", status=TaskStatus.TIMED_OUT).success is False

    def test_duration_field(self):
        r = TaskResult(
            task_id="1", task_name="t", status=TaskStatus.COMPLETED,
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            completed_at=datetime(2026, 1, 1, 0, 0, 1),
            duration_ms=1000,
        )
        assert r.duration_ms == 1000


class TestTaskConfig:
    def test_defaults(self):
        config = TaskConfig(name="test")
        assert config.timeout_seconds == 300
        assert config.max_retries == 0
        assert config.fallback_to_original is True

    def test_custom_values(self):
        config = TaskConfig(name="custom", timeout_seconds=60, max_retries=2, fallback_to_original=False)
        assert config.timeout_seconds == 60
        assert config.max_retries == 2
        assert config.fallback_to_original is False


# ============================================================
# 8. 集成场景
# ============================================================

class TestIntegrationScenarios:
    def test_section_deepen_scenario(self, executor):
        sections = [
            {"id": f"s{i}", "title": f"第{i}章", "content": f"原始内容{i}"}
            for i in range(5)
        ]

        def mock_enhance(section_id, content, vague_points):
            time.sleep(0.02)
            return f"{content} + 深化补充内容"

        tasks = [
            {"name": f"深化-{s['title']}", "fn": mock_enhance, "args": (s["id"], s["content"], [])}
            for s in sections
        ]

        results = executor.run_parallel(tasks, config=TaskConfig(name="content_deepen", timeout_seconds=5))
        assert all(r.success for r in results)
        for i, r in enumerate(results):
            assert f"原始内容{i} + 深化补充内容" == r.result

    def test_coder_artist_parallel_scenario(self, executor):
        mock_state = {"sections": [{"id": "s1", "content": "test"}]}

        def mock_coder(state):
            time.sleep(0.03)
            return {"code_blocks": [{"id": "c1", "code": "print('hello')"}]}

        def mock_artist(state):
            time.sleep(0.05)
            return {"images": [{"id": "img1", "caption": "架构图"}]}

        tasks = [
            {"name": "代码生成", "fn": mock_coder, "args": (mock_state,)},
            {"name": "配图生成", "fn": mock_artist, "args": (mock_state,)},
        ]

        results = executor.run_parallel(tasks)
        assert results[0].success and results[0].result["code_blocks"][0]["id"] == "c1"
        assert results[1].success and results[1].result["images"][0]["id"] == "img1"

    def test_partial_failure_with_fallback(self, executor):
        sections = [
            {"id": "s1", "content": "好内容"},
            {"id": "s2", "content": "原始内容"},
            {"id": "s3", "content": "好内容3"},
        ]

        def mock_enhance(idx):
            if idx == 1:
                raise RuntimeError("LLM API 超时")
            return f"增强后的内容_{idx}"

        tasks = [
            {"name": f"增强-{s['id']}", "fn": mock_enhance, "args": (i,)}
            for i, s in enumerate(sections)
        ]

        config = TaskConfig(name="enhance", fallback_to_original=True)
        results = executor.run_parallel(tasks, config=config)

        assert results[0].success and results[2].success
        assert results[1].status == TaskStatus.FAILED
        assert sections[1]["content"] == "原始内容"  # 未被修改
