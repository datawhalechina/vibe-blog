"""
SchedulerService — APScheduler AsyncIOScheduler 封装

功能：
- Cron/Date 触发器管理
- 到时间后创建 BlogTask 并入队到 TaskQueueManager
- 一次性任务执行后自清理
"""
import json
import logging
import uuid

from .db import TaskDB
from .models import (
    BlogGenerationConfig, BlogTask, PublishConfig,
    TriggerConfig, TriggerType,
)

logger = logging.getLogger(__name__)

# APScheduler 可选依赖
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    AsyncIOScheduler = None


class SchedulerService:
    def __init__(self, queue_manager,
                 db_path: str = "data/task_queue.db"):
        self.queue_manager = queue_manager
        self.db = TaskDB(db_path)
        self._started = False

        if HAS_APSCHEDULER:
            self.scheduler = AsyncIOScheduler(
                timezone='Asia/Shanghai',
            )
        else:
            self.scheduler = None
            logger.warning(
                "[Scheduler] APScheduler 未安装，定时功能不可用"
            )

    def start(self):
        if self.scheduler:
            self.scheduler.start()
            self._started = True
            logger.info("[Scheduler] 定时调度器已启动")

    def shutdown(self):
        if self.scheduler and self._started:
            self.scheduler.shutdown()
            self._started = False

    async def add_task(self, config: dict) -> str:
        """创建定时任务"""
        if not self.scheduler:
            raise RuntimeError("APScheduler 未安装")

        task_id = config.get('id', str(uuid.uuid4())[:8])
        config['id'] = task_id
        trigger_type = config['trigger']['type']

        if trigger_type == 'cron':
            trigger = CronTrigger.from_crontab(
                config['trigger']['cron_expression'],
                timezone=config['trigger'].get(
                    'timezone', 'Asia/Shanghai'
                ),
            )
        elif trigger_type == 'once':
            trigger = DateTrigger(
                run_date=config['trigger']['scheduled_at'],
                timezone=config['trigger'].get(
                    'timezone', 'Asia/Shanghai'
                ),
            )
        else:
            raise ValueError(f"不支持的触发类型: {trigger_type}")

        self.scheduler.add_job(
            func=self._on_trigger,
            trigger=trigger,
            id=f"sched_{task_id}",
            name=config['name'],
            kwargs={'config': config},
            replace_existing=True,
        )

        await self.db.save_scheduled_task(config)
        logger.info(
            f"[Scheduler] 创建定时任务: {task_id} '{config['name']}'"
        )
        return task_id

    async def _on_trigger(self, config: dict):
        """定时触发回调：创建 BlogTask 并入队"""
        task = BlogTask(
            name=f"[定时] {config['name']}",
            trigger=TriggerConfig(
                type=TriggerType(config['trigger']['type']),
                cron_expression=config['trigger'].get(
                    'cron_expression'
                ),
                human_readable=config['trigger'].get(
                    'human_readable'
                ),
            ),
            generation=BlogGenerationConfig(
                **config['generation']
            ),
            publish=PublishConfig(
                **config.get('publish', {})
            ),
            tags=config.get('tags', []) + ['scheduled'],
        )
        await self.queue_manager.enqueue(task)
        logger.info(
            f"[Scheduler] 触发: {config['name']} → 入队 {task.id}"
        )
        # 一次性任务执行后自清理
        if config['trigger']['type'] == 'once':
            await self.remove_task(config['id'])

    async def remove_task(self, task_id: str):
        job_id = f"sched_{task_id}"
        if self.scheduler and self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        await self.db.delete_scheduled_task(task_id)
        logger.info(f"[Scheduler] 删除定时任务: {task_id}")

    async def list_tasks(self) -> list[dict]:
        if not self.scheduler:
            return []
        jobs = self.scheduler.get_jobs()
        db_tasks = await self.db.get_scheduled_tasks()
        db_map = {t['id']: t for t in db_tasks}
        result = []
        for job in jobs:
            tid = job.id.replace('sched_', '')
            db_info = db_map.get(tid, {})
            result.append({
                'id': tid,
                'name': job.name,
                'next_run': str(job.next_run_time)
                    if job.next_run_time else None,
                'trigger': str(job.trigger),
                'enabled': not job.pending,
                'generation_config': db_info.get(
                    'generation_config'
                ),
                'human_readable': db_info.get('human_readable'),
            })
        return result

    async def pause_task(self, task_id: str):
        if self.scheduler:
            self.scheduler.pause_job(f"sched_{task_id}")

    async def resume_task(self, task_id: str):
        if self.scheduler:
            self.scheduler.resume_job(f"sched_{task_id}")
