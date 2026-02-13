"""
test_db.py — TaskDB 异步数据库 CRUD 测试 (D1-D10)
"""
import pytest
import pytest_asyncio
from datetime import datetime

from services.task_queue.models import (
    BlogTask, BlogGenerationConfig, ExecutionRecord,
    QueueStatus, TaskPriority,
)
from services.task_queue.db import TaskDB


@pytest_asyncio.fixture
async def db(tmp_path):
    d = TaskDB(db_path=str(tmp_path / "test.db"))
    await d.init()
    return d


def _make_task(name="测试任务", topic="AI", **kwargs):
    return BlogTask(
        name=name,
        generation=BlogGenerationConfig(topic=topic),
        **kwargs,
    )


class TestTaskCRUD:
    """D1-D6: 任务 CRUD"""

    @pytest.mark.asyncio
    async def test_d1_save_and_get(self, db):
        """D1: 保存并读取任务"""
        task = _make_task()
        await db.save_task(task)
        loaded = await db.get_task(task.id)
        assert loaded is not None
        assert loaded.name == "测试任务"
        assert loaded.generation.topic == "AI"
        assert loaded.status == QueueStatus.QUEUED

    @pytest.mark.asyncio
    async def test_d2_get_nonexistent(self, db):
        """D2: 读取不存在的任务返回 None"""
        assert await db.get_task("nonexistent") is None

    @pytest.mark.asyncio
    async def test_d3_update_status(self, db):
        """D3: 更新任务状态"""
        task = _make_task()
        await db.save_task(task)
        task.status = QueueStatus.RUNNING
        task.progress = 50
        task.started_at = datetime.now()
        await db.save_task(task)
        loaded = await db.get_task(task.id)
        assert loaded.status == QueueStatus.RUNNING
        assert loaded.progress == 50
        assert loaded.started_at is not None

    @pytest.mark.asyncio
    async def test_d4_get_by_status(self, db):
        """D4: 按状态查询"""
        for i in range(3):
            await db.save_task(_make_task(name=f"queued-{i}"))
        running = _make_task(name="running")
        running.status = QueueStatus.RUNNING
        await db.save_task(running)

        queued = await db.get_tasks_by_status(QueueStatus.QUEUED)
        assert len(queued) == 3
        running_list = await db.get_tasks_by_status(QueueStatus.RUNNING)
        assert len(running_list) == 1

    @pytest.mark.asyncio
    async def test_d5_count_by_status(self, db):
        """D5: 按状态计数"""
        for i in range(5):
            await db.save_task(_make_task(name=f"t-{i}"))
        assert await db.count_by_status(QueueStatus.QUEUED) == 5
        assert await db.count_by_status(QueueStatus.RUNNING) == 0

    @pytest.mark.asyncio
    async def test_d6_priority_ordering(self, db):
        """D6: 按优先级排序"""
        low = _make_task(name="low", priority=TaskPriority.LOW)
        high = _make_task(name="high", priority=TaskPriority.HIGH)
        normal = _make_task(name="normal")
        await db.save_task(low)
        await db.save_task(high)
        await db.save_task(normal)
        tasks = await db.get_tasks_by_status(QueueStatus.QUEUED)
        assert tasks[0].name == "high"
        assert tasks[-1].name == "low"


class TestExecutionHistory:
    """D7-D8: 执行历史"""

    @pytest.mark.asyncio
    async def test_d7_save_and_query(self, db):
        """D7: 保存并查询执行记录"""
        record = ExecutionRecord(
            task_id="t1", task_name="测试",
            status=QueueStatus.COMPLETED,
            started_at=datetime.now(),
            duration_ms=5000,
        )
        await db.save_execution_record(record)
        history = await db.get_execution_history(task_id="t1")
        assert len(history) == 1
        assert history[0].duration_ms == 5000

    @pytest.mark.asyncio
    async def test_d8_history_limit(self, db):
        """D8: 历史记录限制"""
        for i in range(10):
            await db.save_execution_record(ExecutionRecord(
                task_id="t1", task_name=f"run-{i}",
                status=QueueStatus.COMPLETED,
                started_at=datetime.now(),
            ))
        history = await db.get_execution_history(limit=5)
        assert len(history) == 5


class TestScheduledTaskCRUD:
    """D9-D10: 定时任务 CRUD"""

    @pytest.mark.asyncio
    async def test_d9_save_and_list(self, db):
        """D9: 保存并列出定时任务"""
        config = {
            'id': 'sched-1', 'name': '每日博客',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI 日报'},
        }
        await db.save_scheduled_task(config)
        tasks = await db.get_scheduled_tasks()
        assert len(tasks) == 1
        assert tasks[0]['name'] == '每日博客'

    @pytest.mark.asyncio
    async def test_d10_delete(self, db):
        """D10: 删除定时任务"""
        config = {
            'id': 'sched-2', 'name': '临时任务',
            'trigger': {'type': 'once', 'scheduled_at': '2026-03-01T15:00:00'},
            'generation': {'topic': '测试'},
        }
        await db.save_scheduled_task(config)
        await db.delete_scheduled_task('sched-2')
        tasks = await db.get_scheduled_tasks()
        assert len(tasks) == 0
