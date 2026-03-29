"""
任务执行器 + 结果处理

对应 OpenClaw: src/cron/service/timer.ts 的 executeJobCore + applyJobResult
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .backoff import error_backoff_seconds
from .models import (
    BlogGenerationConfig, BlogTask, CronJob, CronJobStatus,
    CronScheduleKind, PublishConfig, TriggerConfig, TriggerType,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 600  # 10 分钟


class CronExecutor:
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager

    async def execute(self, job: CronJob) -> dict:
        """
        执行单个任务，返回结果 dict。
        对应 OpenClaw executeJobCore()
        """
        timeout = job.timeout_seconds or DEFAULT_TIMEOUT
        start_time = datetime.now()

        try:
            result = await asyncio.wait_for(
                self._run_blog_task(job),
                timeout=timeout,
            )
            return {
                'status': 'ok',
                'started_at': start_time,
                'ended_at': datetime.now(),
                'summary': result.get('url'),
            }
        except asyncio.TimeoutError:
            return {
                'status': 'error',
                'error': f'执行超时 ({timeout}s)',
                'started_at': start_time,
                'ended_at': datetime.now(),
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'started_at': start_time,
                'ended_at': datetime.now(),
            }

    async def _run_blog_task(self, job: CronJob) -> dict:
        """创建 BlogTask 并入队到 TaskQueueManager"""
        task = BlogTask(
            name=f"[定时] {job.name}",
            trigger=TriggerConfig(type=TriggerType.CRON),
            generation=job.generation,
            publish=job.publish,
            tags=job.tags + ['scheduled'],
        )
        await self.queue_manager.enqueue(task)
        return {'task_id': task.id, 'url': None}

    def apply_result(
        self,
        job: CronJob,
        result: dict,
        compute_next_run_at,
    ) -> bool:
        """
        将执行结果应用到 job 状态。返回 True 表示应删除该 job。
        对应 OpenClaw applyJobResult (timer.ts L48-118)
        """
        started_at = result['started_at']
        ended_at = result['ended_at']
        status = result['status']

        job.state.running_at = None
        job.state.last_run_at = started_at
        job.state.last_status = CronJobStatus(status)
        job.state.last_duration_ms = int(
            (ended_at - started_at).total_seconds() * 1000
        )
        job.state.last_error = result.get('error')
        job.updated_at = ended_at

        if status == 'error':
            job.state.consecutive_errors += 1
        else:
            job.state.consecutive_errors = 0

        # 一次性 at 任务：执行后删除或禁用
        should_delete = (
            job.schedule.kind == CronScheduleKind.AT
            and job.delete_after_run
            and status == 'ok'
        )

        if not should_delete:
            if job.schedule.kind == CronScheduleKind.AT:
                # 一次性任务执行后禁用（对应 OpenClaw timer.ts L76-92）
                job.enabled = False
                job.state.next_run_at = None
            elif status == 'error' and job.enabled:
                # 指数退避（对应 OpenClaw timer.ts L93-109）
                backoff_s = error_backoff_seconds(
                    job.state.consecutive_errors
                )
                normal_next = compute_next_run_at(job.schedule, ended_at)
                backoff_next = ended_at + timedelta(seconds=backoff_s)
                job.state.next_run_at = max(
                    normal_next or backoff_next, backoff_next
                )
                logger.info(
                    f"[CronExecutor] 退避 {backoff_s}s: {job.id} "
                    f"(连续失败 {job.state.consecutive_errors} 次)"
                )
            elif job.enabled:
                job.state.next_run_at = compute_next_run_at(
                    job.schedule, ended_at
                )
            else:
                job.state.next_run_at = None

        return should_delete
