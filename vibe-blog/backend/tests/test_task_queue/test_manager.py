"""
test_manager.py — TaskQueueManager 单元测试 (Q1-Q16)
"""
import asyncio

import pytest

from services.task_queue.models import (
    BlogTask, BlogGenerationConfig, QueueStatus, TaskPriority,
)
from services.task_queue.manager import TaskQueueManager


def _make_task(name="测试任务", topic="AI", **kwargs):
    return BlogTask(
        name=name,
        generation=BlogGenerationConfig(topic=topic),
        **kwargs,
    )


class TestEnqueue:
    """Q1-Q5: 入队操作"""

    @pytest.mark.asyncio
    async def test_q1_enqueue_returns_id(self, queue_manager):
        """Q1: 入队返回 task_id"""
        task = _make_task()
        task_id = await queue_manager.enqueue(task)
        assert task_id == task.id
        assert len(task_id) == 8

    @pytest.mark.asyncio
    async def test_q2_enqueue_sets_position(self, queue_manager):
        """Q2: 入队设置队列位置"""
        t1 = _make_task(name="first")
        t2 = _make_task(name="second")
        await queue_manager.enqueue(t1)
        await queue_manager.enqueue(t2)
        loaded = await queue_manager.get_task(t2.id)
        assert loaded.queue_position == 2

    @pytest.mark.asyncio
    async def test_q3_enqueue_persists(self, queue_manager):
        """Q3: 入队后任务持久化到 DB"""
        task = _make_task()
        await queue_manager.enqueue(task)
        loaded = await queue_manager.db.get_task(task.id)
        assert loaded is not None
        assert loaded.status == QueueStatus.QUEUED


class TestCancel:
    """Q4-Q6: 取消操作"""

    @pytest.mark.asyncio
    async def test_q4_cancel_queued(self, queue_manager):
        """Q4: 取消排队中的任务"""
        task = _make_task()
        await queue_manager.enqueue(task)
        result = await queue_manager.cancel(task.id)
        assert result is True
        loaded = await queue_manager.get_task(task.id)
        assert loaded.status == QueueStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_q5_cancel_nonexistent(self, queue_manager):
        """Q5: 取消不存在的任务返回 False"""
        assert await queue_manager.cancel("nonexistent") is False

    @pytest.mark.asyncio
    async def test_q6_cancel_completed(self, queue_manager):
        """Q6: 不能取消已完成的任务"""
        task = _make_task()
        task.status = QueueStatus.COMPLETED
        await queue_manager.db.save_task(task)
        assert await queue_manager.cancel(task.id) is False


class TestSnapshot:
    """Q7-Q8: 队列快照"""

    @pytest.mark.asyncio
    async def test_q7_empty_snapshot(self, queue_manager):
        """Q7: 空队列快照"""
        snap = await queue_manager.get_queue_snapshot()
        assert snap['stats']['queued_count'] == 0
        assert snap['stats']['running_count'] == 0

    @pytest.mark.asyncio
    async def test_q8_snapshot_with_tasks(self, queue_manager):
        """Q8: 有任务时的快照"""
        for i in range(3):
            await queue_manager.enqueue(_make_task(name=f"t-{i}"))
        snap = await queue_manager.get_queue_snapshot()
        assert snap['stats']['queued_count'] == 3
        assert len(snap['queued']) == 3


class TestWorker:
    """Q9-Q13: Worker 执行"""

    @pytest.mark.asyncio
    async def test_q9_worker_executes_task(self, queue_manager):
        """Q9: Worker 执行任务到完成"""
        task = _make_task()
        await queue_manager.enqueue(task)
        await queue_manager.start_worker()
        # 等待任务完成
        for _ in range(50):
            loaded = await queue_manager.get_task(task.id)
            if loaded.status == QueueStatus.COMPLETED:
                break
            await asyncio.sleep(0.05)
        await queue_manager.stop_worker()
        loaded = await queue_manager.get_task(task.id)
        assert loaded.status == QueueStatus.COMPLETED
        assert loaded.progress == 100
        assert loaded.output_url is not None

    @pytest.mark.asyncio
    async def test_q10_worker_handles_failure(self, queue_manager,
                                               failing_generator):
        """Q10: Worker 处理失败任务"""
        queue_manager.set_blog_generator(failing_generator)
        task = _make_task()
        await queue_manager.enqueue(task)
        await queue_manager.start_worker()
        for _ in range(50):
            loaded = await queue_manager.get_task(task.id)
            if loaded.status == QueueStatus.FAILED:
                break
            await asyncio.sleep(0.05)
        await queue_manager.stop_worker()
        loaded = await queue_manager.get_task(task.id)
        assert loaded.status == QueueStatus.FAILED

    @pytest.mark.asyncio
    async def test_q11_concurrent_limit(self, queue_manager):
        """Q11: 并发控制 — 最多同时执行 max_concurrent 个"""
        # 用慢生成器
        from tests.test_task_queue.conftest import FakeBlogGenerator
        slow = FakeBlogGenerator(delay=0.5)
        queue_manager.set_blog_generator(slow)

        for i in range(4):
            await queue_manager.enqueue(_make_task(name=f"slow-{i}"))
        await queue_manager.start_worker()
        await asyncio.sleep(0.15)
        # 检查同时运行的不超过 2 个
        running = await queue_manager.db.count_by_status(QueueStatus.RUNNING)
        assert running <= queue_manager.max_concurrent
        await queue_manager.stop_worker()

    @pytest.mark.asyncio
    async def test_q12_execution_history_recorded(self, queue_manager):
        """Q12: 执行完成后记录历史"""
        task = _make_task()
        await queue_manager.enqueue(task)
        await queue_manager.start_worker()
        for _ in range(50):
            loaded = await queue_manager.get_task(task.id)
            if loaded.status == QueueStatus.COMPLETED:
                break
            await asyncio.sleep(0.05)
        await queue_manager.stop_worker()
        history = await queue_manager.db.get_execution_history(
            task_id=task.id
        )
        assert len(history) >= 1
        assert history[0].status == QueueStatus.COMPLETED
        assert history[0].duration_ms > 0


class TestPriority:
    """Q13-Q14: 优先级排序"""

    @pytest.mark.asyncio
    async def test_q13_high_priority_first(self, tmp_db_path):
        """Q13: 高优先级任务优先执行"""
        from tests.test_task_queue.conftest import FakeBlogGenerator
        # 用 max_concurrent=1 确保串行执行，验证优先级顺序
        mgr = TaskQueueManager(db_path=tmp_db_path, max_concurrent=1)
        await mgr.init()
        mgr.set_blog_generator(FakeBlogGenerator(delay=0.05))

        completed_order = []

        def on_complete(task):
            completed_order.append(task.name)

        mgr.on('task_completed', on_complete)

        low = _make_task(name="low", priority=TaskPriority.LOW)
        high = _make_task(name="high", priority=TaskPriority.HIGH)
        normal = _make_task(name="normal")

        # 先入队低优先级，再入队高优先级
        await mgr.enqueue(low)
        await mgr.enqueue(normal)
        await mgr.enqueue(high)

        await mgr.start_worker()
        for _ in range(100):
            if len(completed_order) >= 3:
                break
            await asyncio.sleep(0.05)
        await mgr.stop_worker()
        # 高优先级应该最先完成
        assert completed_order[0] == "high"


class TestEvents:
    """Q15-Q16: 事件回调"""

    @pytest.mark.asyncio
    async def test_q15_event_callbacks(self, queue_manager):
        """Q15: 事件回调触发"""
        events = []

        def on_queued(task):
            events.append(('queued', task.id))

        def on_cancelled(task):
            events.append(('cancelled', task.id))

        queue_manager.on('task_queued', on_queued)
        queue_manager.on('task_cancelled', on_cancelled)

        task = _make_task()
        await queue_manager.enqueue(task)
        await queue_manager.cancel(task.id)

        assert ('queued', task.id) in events
        assert ('cancelled', task.id) in events

    @pytest.mark.asyncio
    async def test_q16_async_callback(self, queue_manager):
        """Q16: 异步事件回调"""
        events = []

        async def on_queued(task):
            events.append(task.id)

        queue_manager.on('task_queued', on_queued)
        task = _make_task()
        await queue_manager.enqueue(task)
        assert task.id in events
