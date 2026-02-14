"""
T7: 主调度器 CronScheduler 测试
"""
import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from services.task_queue.models import (
    CronJob, CronSchedule, CronScheduleKind, CronJobState,
    CronJobStatus, BlogGenerationConfig,
)
from services.task_queue.cron_scheduler import CronScheduler


@pytest_asyncio.fixture
async def scheduler():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        mock_queue = MagicMock()
        mock_queue.enqueue = AsyncMock(return_value="task123")
        sched = CronScheduler(mock_queue, db_path=db_path)
        await sched._init_db()
        yield sched
        sched.stop()


# ── CRUD ──

@pytest.mark.asyncio
class TestCRUD:
    async def test_add_cron(self, scheduler):
        job = await scheduler.add({
            'name': '每日博客',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        assert job.id is not None
        assert job.schedule.kind == CronScheduleKind.CRON
        assert job.state.next_run_at is not None

    async def test_add_once(self, scheduler):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        job = await scheduler.add({
            'name': '一次性',
            'trigger': {'type': 'once', 'scheduled_at': future},
            'generation': {'topic': 'AI'},
        })
        assert job.schedule.kind == CronScheduleKind.AT
        assert job.state.next_run_at is not None

    async def test_add_every(self, scheduler):
        job = await scheduler.add({
            'name': '每小时',
            'trigger': {'type': 'every', 'every_seconds': 3600},
            'generation': {'topic': 'AI'},
        })
        assert job.schedule.kind == CronScheduleKind.EVERY
        assert job.state.next_run_at is not None

    async def test_list(self, scheduler):
        await scheduler.add({
            'name': 'job1',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        await scheduler.add({
            'name': 'job2',
            'trigger': {'type': 'cron', 'cron_expression': '0 9 * * *'},
            'generation': {'topic': 'ML'},
        })
        jobs = await scheduler.list_jobs()
        assert len(jobs) == 2

    async def test_remove_existing(self, scheduler):
        job = await scheduler.add({
            'name': 'to_remove',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        assert await scheduler.remove(job.id) is True

    async def test_remove_nonexistent(self, scheduler):
        assert await scheduler.remove('nonexistent') is False

    async def test_update(self, scheduler):
        job = await scheduler.add({
            'name': 'original',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        updated = await scheduler.update(job.id, {'name': 'updated'})
        assert updated.name == 'updated'

    async def test_update_nonexistent(self, scheduler):
        with pytest.raises(ValueError):
            await scheduler.update('nonexistent', {'name': 'x'})


# ── 暂停/恢复 ──

@pytest.mark.asyncio
class TestPauseResume:
    async def test_pause(self, scheduler):
        job = await scheduler.add({
            'name': 'pausable',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        await scheduler.pause(job.id)
        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded.enabled is False
        assert loaded.state.next_run_at is None

    async def test_resume(self, scheduler):
        job = await scheduler.add({
            'name': 'resumable',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        await scheduler.pause(job.id)
        await scheduler.resume(job.id)
        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded.enabled is True
        assert loaded.state.next_run_at is not None


# ── 状态 ──

@pytest.mark.asyncio
class TestStatus:
    async def test_status_empty(self, scheduler):
        s = await scheduler.status()
        assert s['enabled'] is True
        assert s['total_jobs'] == 0
        assert s['enabled_jobs'] == 0

    async def test_status_with_jobs(self, scheduler):
        await scheduler.add({
            'name': 'job1',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        s = await scheduler.status()
        assert s['total_jobs'] == 1
        assert s['enabled_jobs'] == 1
        assert s['next_wake_at'] is not None


# ── 启动恢复 ──

@pytest.mark.asyncio
class TestRecovery:
    async def test_clears_stale_running(self, scheduler):
        """启动时清除残留 running_at"""
        job = await scheduler.add({
            'name': 'stale',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.state.running_at = datetime.now() - timedelta(hours=3)
        await scheduler.db.save_cron_job(job)

        await scheduler._startup_recovery()
        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded.state.running_at is None

    async def test_runs_missed_jobs(self, scheduler):
        """补执行错过的任务"""
        job = await scheduler.add({
            'name': 'missed',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.state.next_run_at = datetime.now() - timedelta(hours=1)
        await scheduler.db.save_cron_job(job)

        await scheduler._run_missed_jobs()
        scheduler.executor.queue_manager.enqueue.assert_awaited()


# ── 卡死检测 ──

@pytest.mark.asyncio
class TestStuckDetection:
    async def test_stuck_job_cleared(self, scheduler):
        """running_at > 2h 的任务被清除"""
        job = await scheduler.add({
            'name': 'stuck',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.state.running_at = datetime.now() - timedelta(hours=3)
        await scheduler.db.save_cron_job(job)

        await scheduler._check_stuck_jobs()
        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded.state.running_at is None

    async def test_non_stuck_job_kept(self, scheduler):
        """running_at < 2h 的任务不被清除"""
        job = await scheduler.add({
            'name': 'running',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        running_at = datetime.now() - timedelta(minutes=30)
        job.state.running_at = running_at
        await scheduler.db.save_cron_job(job)

        await scheduler._check_stuck_jobs()
        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded.state.running_at is not None


# ── 自动禁用 ──

@pytest.mark.asyncio
class TestAutoDisable:
    async def test_schedule_error_auto_disable(self, scheduler):
        """调度计算连续失败 3 次 → 自动禁用"""
        job = await scheduler.add({
            'name': 'bad_cron',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.state.schedule_error_count = 2
        job.schedule.expr = "invalid cron that will fail"
        await scheduler.db.save_cron_job(job)

        await scheduler._recompute_next_runs()

        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded.enabled is False
        assert loaded.state.schedule_error_count >= 3


# ── Tick 流程 ──

@pytest.mark.asyncio
class TestTick:
    async def test_tick_executes_due_jobs(self, scheduler):
        """tick 执行到期任务"""
        job = await scheduler.add({
            'name': 'due',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.state.next_run_at = datetime.now() - timedelta(seconds=1)
        await scheduler.db.save_cron_job(job)

        await scheduler._tick()
        scheduler.executor.queue_manager.enqueue.assert_awaited()

    async def test_tick_skips_running_jobs(self, scheduler):
        """tick 跳过正在运行的任务"""
        job = await scheduler.add({
            'name': 'running',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.state.next_run_at = datetime.now() - timedelta(seconds=1)
        job.state.running_at = datetime.now()
        await scheduler.db.save_cron_job(job)

        await scheduler._tick()
        scheduler.executor.queue_manager.enqueue.assert_not_awaited()

    async def test_tick_skips_disabled_jobs(self, scheduler):
        """tick 跳过禁用的任务"""
        job = await scheduler.add({
            'name': 'disabled',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })
        job.enabled = False
        job.state.next_run_at = datetime.now() - timedelta(seconds=1)
        await scheduler.db.save_cron_job(job)

        await scheduler._tick()
        scheduler.executor.queue_manager.enqueue.assert_not_awaited()

    async def test_tick_deletes_one_shot_after_success(self, scheduler):
        """一次性任务成功后删除（delete_after_run=True）"""
        future = (datetime.now() + timedelta(seconds=1)).isoformat()
        job = await scheduler.add({
            'name': 'one_shot',
            'trigger': {'type': 'once', 'scheduled_at': future},
            'generation': {'topic': 'AI'},
            'delete_after_run': True,
        })
        job.state.next_run_at = datetime.now() - timedelta(seconds=1)
        await scheduler.db.save_cron_job(job)

        await scheduler._tick()
        loaded = await scheduler.db.get_cron_job(job.id)
        assert loaded is None  # 已删除
