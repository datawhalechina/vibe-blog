"""
T9: 数据迁移测试 scheduled_tasks → cron_jobs
"""
import pytest
import pytest_asyncio
import tempfile
import os
from services.task_queue.db import TaskDB
from services.task_queue.models import CronScheduleKind


@pytest_asyncio.fixture
async def db_with_old_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = TaskDB(db_path)
        await db.init()
        yield db, db_path


@pytest.mark.asyncio
class TestMigration:
    async def test_migrate_cron_task(self, db_with_old_data):
        """cron 类型任务正确迁移"""
        db, db_path = db_with_old_data
        await db.save_scheduled_task({
            'id': 'old01',
            'name': '旧任务',
            'trigger': {
                'type': 'cron',
                'cron_expression': '0 8 * * *',
                'timezone': 'Asia/Shanghai',
            },
            'generation': {'topic': 'AI'},
        })

        from services.task_queue.migrate_to_cron_jobs import migrate
        count = await migrate(db_path)
        assert count == 1

        job = await db.get_cron_job('old01')
        assert job is not None
        assert job.schedule.kind == CronScheduleKind.CRON
        assert job.schedule.expr == '0 8 * * *'
        assert job.name == '旧任务'
        assert job.generation.topic == 'AI'

    async def test_migrate_once_task(self, db_with_old_data):
        """once 类型任务映射为 at"""
        db, db_path = db_with_old_data
        await db.save_scheduled_task({
            'id': 'old02',
            'name': '一次性旧任务',
            'trigger': {
                'type': 'once',
                'scheduled_at': '2025-06-01T12:00:00',
            },
            'generation': {'topic': 'AI'},
        })

        from services.task_queue.migrate_to_cron_jobs import migrate
        count = await migrate(db_path)
        assert count == 1

        job = await db.get_cron_job('old02')
        assert job is not None
        assert job.schedule.kind == CronScheduleKind.AT

    async def test_migrate_idempotent(self, db_with_old_data):
        """迁移幂等：重复执行不报错"""
        db, db_path = db_with_old_data
        await db.save_scheduled_task({
            'id': 'old03', 'name': 'test',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })

        from services.task_queue.migrate_to_cron_jobs import migrate
        await migrate(db_path)
        await migrate(db_path)  # 第二次不应报错

        jobs = await db.get_cron_jobs()
        assert len(jobs) == 1

    async def test_migrate_preserves_old_data(self, db_with_old_data):
        """迁移后旧表数据保留"""
        db, db_path = db_with_old_data
        await db.save_scheduled_task({
            'id': 'old04', 'name': 'keep',
            'trigger': {'type': 'cron', 'cron_expression': '0 8 * * *'},
            'generation': {'topic': 'AI'},
        })

        from services.task_queue.migrate_to_cron_jobs import migrate
        await migrate(db_path)

        old_tasks = await db.get_scheduled_tasks()
        assert len(old_tasks) == 1  # 旧数据仍在

    async def test_migrate_empty(self, db_with_old_data):
        """空表迁移不报错"""
        _, db_path = db_with_old_data
        from services.task_queue.migrate_to_cron_jobs import migrate
        count = await migrate(db_path)
        assert count == 0
