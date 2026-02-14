"""
T3: Cron Job 数据库 CRUD 测试
"""
import pytest
import pytest_asyncio
import tempfile
import os
from datetime import datetime
from services.task_queue.db import TaskDB
from services.task_queue.models import (
    CronJob, CronSchedule, CronScheduleKind, CronJobState,
    CronJobStatus, BlogGenerationConfig, PublishConfig,
)


@pytest_asyncio.fixture
async def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        task_db = TaskDB(db_path)
        await task_db.init()
        yield task_db


@pytest.fixture
def sample_job():
    return CronJob(
        id="test001",
        name="每日博客",
        schedule=CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *"),
        generation=BlogGenerationConfig(topic="AI 入门"),
        tags=["daily"],
    )


@pytest.mark.asyncio
class TestCronJobCRUD:
    async def test_save_and_get(self, db, sample_job):
        await db.save_cron_job(sample_job)
        loaded = await db.get_cron_job("test001")
        assert loaded is not None
        assert loaded.name == "每日博客"
        assert loaded.schedule.expr == "0 8 * * *"
        assert loaded.schedule.kind == CronScheduleKind.CRON
        assert loaded.generation.topic == "AI 入门"
        assert loaded.tags == ["daily"]

    async def test_get_nonexistent(self, db):
        assert await db.get_cron_job("nonexistent") is None

    async def test_get_all(self, db, sample_job):
        await db.save_cron_job(sample_job)
        job2 = CronJob(
            id="test002", name="周报",
            schedule=CronSchedule(kind=CronScheduleKind.CRON, expr="0 9 * * 1"),
            generation=BlogGenerationConfig(topic="周报"),
        )
        await db.save_cron_job(job2)
        jobs = await db.get_cron_jobs()
        assert len(jobs) == 2

    async def test_get_enabled_only(self, db, sample_job):
        sample_job.enabled = False
        await db.save_cron_job(sample_job)
        jobs = await db.get_cron_jobs(include_disabled=False)
        assert len(jobs) == 0
        jobs_all = await db.get_cron_jobs(include_disabled=True)
        assert len(jobs_all) == 1

    async def test_update_via_save(self, db, sample_job):
        await db.save_cron_job(sample_job)
        sample_job.name = "更新后的名称"
        sample_job.state.consecutive_errors = 3
        await db.save_cron_job(sample_job)
        loaded = await db.get_cron_job("test001")
        assert loaded.name == "更新后的名称"
        assert loaded.state.consecutive_errors == 3

    async def test_delete_existing(self, db, sample_job):
        await db.save_cron_job(sample_job)
        assert await db.delete_cron_job("test001") is True
        assert await db.get_cron_job("test001") is None

    async def test_delete_nonexistent(self, db):
        assert await db.delete_cron_job("nonexistent") is False

    async def test_state_roundtrip(self, db, sample_job):
        """验证所有 state 字段正确持久化"""
        sample_job.state = CronJobState(
            next_run_at=datetime(2025, 3, 1, 8, 0),
            running_at=datetime(2025, 3, 1, 7, 59),
            last_run_at=datetime(2025, 2, 28, 8, 0),
            last_status=CronJobStatus.ERROR,
            last_error="timeout",
            last_duration_ms=5000,
            consecutive_errors=2,
            schedule_error_count=1,
        )
        await db.save_cron_job(sample_job)
        loaded = await db.get_cron_job("test001")
        assert loaded.state.next_run_at == datetime(2025, 3, 1, 8, 0)
        assert loaded.state.running_at == datetime(2025, 3, 1, 7, 59)
        assert loaded.state.last_status == CronJobStatus.ERROR
        assert loaded.state.last_error == "timeout"
        assert loaded.state.consecutive_errors == 2
        assert loaded.state.last_duration_ms == 5000
        assert loaded.state.schedule_error_count == 1

    async def test_at_schedule_roundtrip(self, db):
        job = CronJob(
            id="at01", name="一次性",
            schedule=CronSchedule(
                kind=CronScheduleKind.AT,
                at=datetime(2025, 6, 1, 12, 0),
            ),
            generation=BlogGenerationConfig(topic="test"),
        )
        await db.save_cron_job(job)
        loaded = await db.get_cron_job("at01")
        assert loaded.schedule.kind == CronScheduleKind.AT
        assert loaded.schedule.at == datetime(2025, 6, 1, 12, 0)

    async def test_every_schedule_roundtrip(self, db):
        job = CronJob(
            id="ev01", name="每小时",
            schedule=CronSchedule(
                kind=CronScheduleKind.EVERY,
                every_seconds=3600,
                anchor_at=datetime(2025, 1, 1, 0, 0),
            ),
            generation=BlogGenerationConfig(topic="test"),
        )
        await db.save_cron_job(job)
        loaded = await db.get_cron_job("ev01")
        assert loaded.schedule.kind == CronScheduleKind.EVERY
        assert loaded.schedule.every_seconds == 3600
        assert loaded.schedule.anchor_at == datetime(2025, 1, 1, 0, 0)

    async def test_publish_config_roundtrip(self, db):
        job = CronJob(
            id="pub01", name="发布测试",
            schedule=CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *"),
            generation=BlogGenerationConfig(topic="test"),
            publish=PublishConfig(auto_publish=True, platform="wechat"),
        )
        await db.save_cron_job(job)
        loaded = await db.get_cron_job("pub01")
        assert loaded.publish.auto_publish is True
        assert loaded.publish.platform == "wechat"
