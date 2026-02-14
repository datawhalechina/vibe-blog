"""
CronScheduler — 纯 Python 自驱动调度器

移植自 OpenClaw src/cron/ 设计：
- asyncio.call_later 自驱动循环（替代 setTimeout）
- croniter 解析 cron 表达式（替代 croner）
- SQLite 持久化（替代 JSON 文件）
- 指数退避 + 卡死检测 + 重启恢复
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter

from .backoff import error_backoff_seconds
from .cron_executor import CronExecutor
from .cron_timer import CronTimer, STUCK_RUN_SECONDS
from .db import TaskDB
from .models import (
    BlogGenerationConfig, CronJob, CronJobState, CronJobStatus,
    CronSchedule, CronScheduleKind, PublishConfig,
)

logger = logging.getLogger(__name__)

MAX_SCHEDULE_ERRORS = 3


def compute_next_run_at(
    schedule: CronSchedule, now: datetime
) -> Optional[datetime]:
    """
    计算下一次执行时间。
    对应 OpenClaw: src/cron/service/jobs.ts computeNextRunAtMs()
    """
    kind = schedule.kind

    if kind == CronScheduleKind.AT:
        if schedule.at is None:
            return None
        return schedule.at if schedule.at >= now else None

    elif kind == CronScheduleKind.EVERY:
        if not schedule.every_seconds:
            return None
        interval = schedule.every_seconds
        anchor = schedule.anchor_at
        if anchor is None:
            return now + timedelta(seconds=interval)
        if now < anchor:
            return anchor
        elapsed = (now - anchor).total_seconds()
        periods = int(elapsed / interval) + 1
        return anchor + timedelta(seconds=periods * interval)

    elif kind == CronScheduleKind.CRON:
        if not schedule.expr:
            return None
        try:
            cron = croniter(schedule.expr, now)
            next_dt = cron.get_next(datetime)
            return next_dt
        except (ValueError, KeyError):
            return None

    return None


class CronScheduler:
    """
    自驱动调度器 — 对应 OpenClaw CronService

    生命周期: __init__ → _init_db → start → (运行中) → stop
    """

    def __init__(
        self,
        queue_manager,
        db_path: str = "data/task_queue.db",
        enabled: bool = True,
    ):
        self.db = TaskDB(db_path)
        self.executor = CronExecutor(queue_manager)
        self._enabled = enabled
        self._lock = asyncio.Lock()
        self._timer = CronTimer(
            get_next_wake_at=self._get_next_wake_at,
            tick=self._tick,
            check_stuck=self._check_stuck_jobs,
            enabled=enabled,
        )

    async def _init_db(self):
        await self.db.init()

    # ── 启动 / 停止 ──

    async def start(self):
        """
        启动调度器。
        对应 OpenClaw: src/cron/service/ops.ts start()
        """
        await self._init_db()
        await self._startup_recovery()
        await self._recompute_next_runs()
        self._timer.start()
        logger.info("[CronScheduler] 调度器已启动")

    def stop(self):
        self._timer.stop()
        logger.info("[CronScheduler] 调度器已停止")

    # ── CRUD API ──

    async def add(self, config: dict) -> CronJob:
        """创建定时任务"""
        async with self._lock:
            schedule = self._parse_schedule(config)
            job = CronJob(
                id=config.get('id', str(uuid.uuid4())[:8]),
                name=config['name'],
                description=config.get('description'),
                enabled=config.get('enabled', True),
                delete_after_run=config.get('delete_after_run', False),
                schedule=schedule,
                generation=BlogGenerationConfig(**config['generation']),
                publish=PublishConfig(**config.get('publish', {})),
                timeout_seconds=config.get('timeout_seconds', 600),
                tags=config.get('tags', []),
                user_id=config.get('user_id'),
            )
            job.state.next_run_at = compute_next_run_at(
                job.schedule, datetime.now()
            )
            await self.db.save_cron_job(job)
            logger.info(
                f"[CronScheduler] 添加任务: {job.id} '{job.name}' "
                f"next_run_at={job.state.next_run_at}"
            )
        await self._timer.arm()
        return job

    async def update(self, job_id: str, patch: dict) -> CronJob:
        """部分更新任务"""
        async with self._lock:
            job = await self.db.get_cron_job(job_id)
            if not job:
                raise ValueError(f"任务不存在: {job_id}")

            if 'name' in patch:
                job.name = patch['name']
            if 'description' in patch:
                job.description = patch['description']
            if 'enabled' in patch:
                job.enabled = patch['enabled']
            if 'timeout_seconds' in patch:
                job.timeout_seconds = patch['timeout_seconds']
            if 'tags' in patch:
                job.tags = patch['tags']
            if 'trigger' in patch:
                job.schedule = self._parse_schedule(
                    {'trigger': patch['trigger']}
                )
            if 'generation' in patch:
                job.generation = BlogGenerationConfig(**patch['generation'])
            if 'publish' in patch:
                job.publish = PublishConfig(**patch['publish'])

            if job.enabled:
                job.state.next_run_at = compute_next_run_at(
                    job.schedule, datetime.now()
                )
            else:
                job.state.next_run_at = None

            job.updated_at = datetime.now()
            await self.db.save_cron_job(job)
        await self._timer.arm()
        return job

    async def remove(self, job_id: str) -> bool:
        async with self._lock:
            return await self.db.delete_cron_job(job_id)

    async def list_jobs(self, include_disabled: bool = True) -> list[CronJob]:
        return await self.db.get_cron_jobs(include_disabled=include_disabled)

    async def status(self) -> dict:
        jobs = await self.db.get_cron_jobs()
        enabled_jobs = [j for j in jobs if j.enabled]
        next_wake = await self._get_next_wake_at()
        return {
            'enabled': self._enabled,
            'total_jobs': len(jobs),
            'enabled_jobs': len(enabled_jobs),
            'next_wake_at': next_wake.isoformat() if next_wake else None,
        }

    # ── 暂停 / 恢复 / 重试 / 手动触发 ──

    async def pause(self, job_id: str):
        async with self._lock:
            job = await self.db.get_cron_job(job_id)
            if not job:
                raise ValueError(f"任务不存在: {job_id}")
            job.enabled = False
            job.state.next_run_at = None
            job.updated_at = datetime.now()
            await self.db.save_cron_job(job)

    async def resume(self, job_id: str):
        async with self._lock:
            job = await self.db.get_cron_job(job_id)
            if not job:
                raise ValueError(f"任务不存在: {job_id}")
            job.enabled = True
            job.state.next_run_at = compute_next_run_at(
                job.schedule, datetime.now()
            )
            job.state.consecutive_errors = 0
            job.updated_at = datetime.now()
            await self.db.save_cron_job(job)
        await self._timer.arm()

    async def retry(self, job_id: str):
        async with self._lock:
            job = await self.db.get_cron_job(job_id)
            if not job:
                raise ValueError(f"任务不存在: {job_id}")
            job.enabled = True
            job.state.consecutive_errors = 0
            job.state.schedule_error_count = 0
            job.state.next_run_at = datetime.now()
            job.updated_at = datetime.now()
            await self.db.save_cron_job(job)
        await self._timer.arm()

    async def run(self, job_id: str, mode: str = 'force') -> dict:
        """手动触发执行"""
        job = await self.db.get_cron_job(job_id)
        if not job:
            return {'ok': False, 'error': '任务不存在'}
        if job.state.running_at:
            return {'ok': False, 'error': 'already-running'}
        if mode == 'due' and (
            not job.state.next_run_at
            or job.state.next_run_at > datetime.now()
        ):
            return {'ok': False, 'error': 'not-due'}

        await self._execute_job(job)
        return {'ok': True, 'ran': True}

    # ── 定时器回调 ──

    async def _get_next_wake_at(self) -> Optional[datetime]:
        jobs = await self.db.get_cron_jobs(include_disabled=False)
        candidates = [
            j.state.next_run_at for j in jobs
            if j.state.next_run_at and not j.state.running_at
        ]
        return min(candidates) if candidates else None

    async def _tick(self):
        """
        定时器触发：找到到期任务并执行。
        对应 OpenClaw: src/cron/service/timer.ts onTimer()
        """
        now = datetime.now()
        jobs = await self.db.get_cron_jobs(include_disabled=False)
        due_jobs = [
            j for j in jobs
            if j.state.next_run_at
            and j.state.next_run_at <= now
            and not j.state.running_at
        ]

        for job in due_jobs:
            await self._execute_job(job)

    async def _execute_job(self, job: CronJob):
        """执行单个任务"""
        async with self._lock:
            job.state.running_at = datetime.now()
            await self.db.save_cron_job(job)

        result = await self.executor.execute(job)

        async with self._lock:
            fresh_job = await self.db.get_cron_job(job.id)
            if not fresh_job:
                return

            should_delete = self.executor.apply_result(
                fresh_job, result, compute_next_run_at
            )

            if should_delete:
                await self.db.delete_cron_job(fresh_job.id)
                logger.info(
                    f"[CronScheduler] 一次性任务已删除: {fresh_job.id}"
                )
            else:
                await self.db.save_cron_job(fresh_job)

    # ── 启动恢复 ──

    async def _startup_recovery(self):
        """
        清除残留 running_at + 补执行错过的任务。
        对应 OpenClaw: src/cron/service/ops.ts start()
        """
        async with self._lock:
            jobs = await self.db.get_cron_jobs()
            for job in jobs:
                if job.state.running_at:
                    logger.warning(
                        f"[CronScheduler] 清除残留 running_at: "
                        f"{job.id} '{job.name}'"
                    )
                    job.state.running_at = None
                    await self.db.save_cron_job(job)

        await self._run_missed_jobs()

    async def _run_missed_jobs(self):
        """补执行错过的任务"""
        now = datetime.now()
        jobs = await self.db.get_cron_jobs(include_disabled=False)
        missed = [
            j for j in jobs
            if j.state.next_run_at
            and j.state.next_run_at < now
            and not j.state.running_at
        ]
        for job in missed:
            logger.info(
                f"[CronScheduler] 补执行错过的任务: "
                f"{job.id} '{job.name}'"
            )
            await self._execute_job(job)

    # ── 卡死检测 ──

    async def _check_stuck_jobs(self):
        """
        running_at > STUCK_RUN_SECONDS → 清除。
        对应 OpenClaw: src/cron/service/timer.ts STUCK_RUN_MS
        """
        now = datetime.now()
        threshold = now - timedelta(seconds=STUCK_RUN_SECONDS)
        async with self._lock:
            jobs = await self.db.get_cron_jobs()
            for job in jobs:
                if (
                    job.state.running_at
                    and job.state.running_at < threshold
                ):
                    logger.warning(
                        f"[CronScheduler] 卡死任务已清除: "
                        f"{job.id} (running since {job.state.running_at})"
                    )
                    job.state.running_at = None
                    job.state.last_status = CronJobStatus.ERROR
                    job.state.last_error = "stuck: 执行超过 2 小时"
                    job.state.consecutive_errors += 1
                    await self.db.save_cron_job(job)

    # ── 调度重算 ──

    async def _recompute_next_runs(self):
        """
        重算所有 enabled job 的 next_run_at。
        对应 OpenClaw: src/cron/service/jobs.ts recomputeNextRuns()
        """
        now = datetime.now()
        async with self._lock:
            jobs = await self.db.get_cron_jobs()
            for job in jobs:
                if not job.enabled:
                    continue
                try:
                    next_at = compute_next_run_at(job.schedule, now)
                    # cron/every 类型有表达式但返回 None → 视为调度计算失败
                    has_expr = (
                        (job.schedule.kind == CronScheduleKind.CRON and job.schedule.expr)
                        or (job.schedule.kind == CronScheduleKind.EVERY and job.schedule.every_seconds)
                    )
                    if next_at is None and has_expr:
                        raise ValueError(
                            f"无法计算下次执行时间 (kind={job.schedule.kind.value})"
                        )
                    job.state.next_run_at = next_at
                    job.state.schedule_error_count = 0
                    await self.db.save_cron_job(job)
                except Exception as e:
                    job.state.schedule_error_count += 1
                    logger.warning(
                        f"[CronScheduler] 调度计算失败: {job.id} "
                        f"({job.state.schedule_error_count}次) - {e}"
                    )
                    if job.state.schedule_error_count >= MAX_SCHEDULE_ERRORS:
                        job.enabled = False
                        logger.error(
                            f"[CronScheduler] 自动禁用: {job.id} "
                            f"(调度计算连续失败 {MAX_SCHEDULE_ERRORS} 次)"
                        )
                    await self.db.save_cron_job(job)

    # ── 内部工具 ──

    @staticmethod
    def _parse_schedule(config: dict) -> CronSchedule:
        trigger = config.get('trigger', {})
        trigger_type = trigger.get('type', 'cron')
        tz = trigger.get('timezone', 'Asia/Shanghai')

        if trigger_type == 'cron':
            return CronSchedule(
                kind=CronScheduleKind.CRON,
                expr=trigger.get('cron_expression'),
                tz=tz,
            )
        elif trigger_type in ('once', 'at'):
            at_str = trigger.get('scheduled_at')
            at = datetime.fromisoformat(at_str) if at_str else None
            return CronSchedule(
                kind=CronScheduleKind.AT,
                at=at,
                tz=tz,
            )
        elif trigger_type == 'every':
            anchor_str = trigger.get('anchor_at')
            anchor = (
                datetime.fromisoformat(anchor_str) if anchor_str else None
            )
            return CronSchedule(
                kind=CronScheduleKind.EVERY,
                every_seconds=trigger.get('every_seconds'),
                anchor_at=anchor,
                tz=tz,
            )
        else:
            raise ValueError(f"不支持的触发类型: {trigger_type}")
