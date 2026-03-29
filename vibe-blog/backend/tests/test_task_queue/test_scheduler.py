"""
test_scheduler.py — SchedulerService 测试 (S1-S6)
"""
import pytest
import pytest_asyncio

from services.task_queue.manager import TaskQueueManager
from services.task_queue.scheduler import SchedulerService

# 检查 APScheduler 是否可用
try:
    import apscheduler
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

pytestmark = pytest.mark.skipif(
    not HAS_APSCHEDULER,
    reason="APScheduler not installed",
)


@pytest_asyncio.fixture
async def scheduler_env(tmp_path):
    """创建 Manager + Scheduler 环境"""
    from tests.test_task_queue.conftest import FakeBlogGenerator
    db_path = str(tmp_path / "sched_test.db")
    mgr = TaskQueueManager(db_path=db_path, max_concurrent=2)
    await mgr.init()
    mgr.set_blog_generator(FakeBlogGenerator(delay=0.01))
    sched = SchedulerService(mgr, db_path=db_path)
    sched.start()
    yield mgr, sched
    sched.shutdown()


class TestSchedulerService:
    """S1-S6: 定时任务管理"""

    @pytest.mark.asyncio
    async def test_s1_add_cron_task(self, scheduler_env):
        """S1: 添加 Cron 定时任务"""
        mgr, sched = scheduler_env
        task_id = await sched.add_task({
            'name': '每日博客',
            'trigger': {
                'type': 'cron',
                'cron_expression': '0 8 * * *',
            },
            'generation': {'topic': 'AI 日报'},
        })
        assert task_id is not None
        tasks = await sched.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]['name'] == '每日博客'

    @pytest.mark.asyncio
    async def test_s2_remove_task(self, scheduler_env):
        """S2: 删除定时任务"""
        mgr, sched = scheduler_env
        task_id = await sched.add_task({
            'name': '临时任务',
            'trigger': {
                'type': 'cron',
                'cron_expression': '*/5 * * * *',
            },
            'generation': {'topic': '测试'},
        })
        await sched.remove_task(task_id)
        tasks = await sched.list_tasks()
        assert len(tasks) == 0

    @pytest.mark.asyncio
    async def test_s3_pause_resume(self, scheduler_env):
        """S3: 暂停/恢复定时任务"""
        mgr, sched = scheduler_env
        task_id = await sched.add_task({
            'name': '可暂停任务',
            'trigger': {
                'type': 'cron',
                'cron_expression': '0 9 * * *',
            },
            'generation': {'topic': '测试'},
        })
        await sched.pause_task(task_id)
        tasks = await sched.list_tasks()
        # paused job has next_run = None
        assert tasks[0]['next_run'] is None

        await sched.resume_task(task_id)
        tasks = await sched.list_tasks()
        assert tasks[0]['next_run'] is not None

    @pytest.mark.asyncio
    async def test_s4_invalid_trigger_type(self, scheduler_env):
        """S4: 不支持的触发类型"""
        mgr, sched = scheduler_env
        with pytest.raises(ValueError, match="不支持"):
            await sched.add_task({
                'name': '错误任务',
                'trigger': {'type': 'invalid'},
                'generation': {'topic': '测试'},
            })

    @pytest.mark.asyncio
    async def test_s5_db_persistence(self, scheduler_env):
        """S5: 定时任务配置持久化到 DB"""
        mgr, sched = scheduler_env
        await sched.add_task({
            'name': '持久化测试',
            'trigger': {
                'type': 'cron',
                'cron_expression': '0 10 * * *',
            },
            'generation': {'topic': 'AI'},
        })
        db_tasks = await sched.db.get_scheduled_tasks()
        assert len(db_tasks) == 1
        assert db_tasks[0]['name'] == '持久化测试'

    @pytest.mark.asyncio
    async def test_s6_multiple_tasks(self, scheduler_env):
        """S6: 多个定时任务共存"""
        mgr, sched = scheduler_env
        for i in range(3):
            await sched.add_task({
                'name': f'任务-{i}',
                'trigger': {
                    'type': 'cron',
                    'cron_expression': f'0 {8+i} * * *',
                },
                'generation': {'topic': f'主题-{i}'},
            })
        tasks = await sched.list_tasks()
        assert len(tasks) == 3
