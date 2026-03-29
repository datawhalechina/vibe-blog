"""
数据迁移脚本：scheduled_tasks → cron_jobs

将旧的 APScheduler 定时任务迁移到新的 CronJob 格式。
- cron 类型 → CronScheduleKind.CRON
- once 类型 → CronScheduleKind.AT
- 旧表数据保留不删除
- 幂等：重复执行不报错（INSERT OR REPLACE）
"""
import json
import logging

import aiosqlite

from .db import TaskDB
from .models import (
    BlogGenerationConfig, CronJob, CronSchedule, CronScheduleKind,
    PublishConfig,
)

logger = logging.getLogger(__name__)


async def migrate(db_path: str) -> int:
    """
    迁移 scheduled_tasks → cron_jobs，返回迁移数量。
    """
    db = TaskDB(db_path)
    await db.init()

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM scheduled_tasks ORDER BY created_at"
        ) as cursor:
            rows = await cursor.fetchall()

    count = 0
    for row in rows:
        row = dict(row)
        try:
            job = _convert_row(row)
            await db.save_cron_job(job)
            count += 1
            logger.info(
                f"[Migration] 迁移成功: {job.id} '{job.name}' "
                f"({job.schedule.kind.value})"
            )
        except Exception as e:
            logger.error(
                f"[Migration] 迁移失败: {row.get('id')} - {e}"
            )

    logger.info(f"[Migration] 迁移完成: {count}/{len(rows)} 个任务")
    return count


def _convert_row(row: dict) -> CronJob:
    """将 scheduled_tasks 行转换为 CronJob"""
    trigger_type = row.get('trigger_type', 'cron')

    if trigger_type == 'cron':
        schedule = CronSchedule(
            kind=CronScheduleKind.CRON,
            expr=row.get('cron_expression'),
            tz=row.get('timezone') or 'Asia/Shanghai',
        )
    elif trigger_type == 'once':
        from datetime import datetime
        at_str = row.get('scheduled_at')
        at = datetime.fromisoformat(at_str) if at_str else None
        schedule = CronSchedule(
            kind=CronScheduleKind.AT,
            at=at,
            tz=row.get('timezone') or 'Asia/Shanghai',
        )
    else:
        raise ValueError(f"未知触发类型: {trigger_type}")

    gen_raw = row.get('generation_config', '{}')
    gen_data = json.loads(gen_raw) if isinstance(gen_raw, str) else gen_raw

    pub_raw = row.get('publish_config', '{}')
    pub_data = json.loads(pub_raw) if isinstance(pub_raw, str) else pub_raw

    return CronJob(
        id=row['id'],
        name=row['name'],
        description=row.get('description'),
        enabled=bool(row.get('enabled', 1)),
        schedule=schedule,
        generation=BlogGenerationConfig(**gen_data),
        publish=PublishConfig(**pub_data),
        tags=json.loads(row.get('tags') or '[]'),
    )
