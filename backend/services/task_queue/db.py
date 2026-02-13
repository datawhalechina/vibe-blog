"""
task_queue 数据库层 — aiosqlite 异步 CRUD

功能：
- 任务 CRUD (save/get/count/list)
- 执行历史记录
- 定时任务配置 CRUD
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from .models import (
    BlogTask, BlogGenerationConfig, ExecutionRecord,
    PublishConfig, QueueStatus, TriggerConfig,
)

logger = logging.getLogger(__name__)


class TaskDB:
    def __init__(self, db_path: str = "data/task_queue.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    async def init(self):
        """初始化数据库表"""
        schema_path = Path(__file__).parent / "schema.sql"
        async with aiosqlite.connect(self.db_path) as db:
            with open(schema_path) as f:
                await db.executescript(f.read())
            await db.commit()

    # ── 任务 CRUD ──

    async def save_task(self, task: BlogTask):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO task_queue
                (id, name, description, trigger_config, generation_config,
                 publish_config, status, priority, queue_position,
                 progress, current_stage, stage_detail,
                 output_url, output_word_count, output_image_count,
                 created_at, updated_at, started_at, completed_at,
                 tags, user_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                task.id, task.name, task.description,
                task.trigger.model_dump_json(),
                task.generation.model_dump_json(),
                task.publish.model_dump_json(),
                task.status.value, task.priority.value, task.queue_position,
                task.progress, task.current_stage, task.stage_detail,
                task.output_url, task.output_word_count, task.output_image_count,
                task.created_at.isoformat(), task.updated_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                json.dumps(task.tags), task.user_id,
            ))
            await db.commit()

    async def get_task(self, task_id: str) -> Optional[BlogTask]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM task_queue WHERE id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_task(dict(row))
        return None

    async def get_tasks_by_status(
        self, status: QueueStatus, limit: int = 50
    ) -> list[BlogTask]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM task_queue WHERE status = ? "
                "ORDER BY priority DESC, created_at ASC LIMIT ?",
                (status.value, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(dict(r)) for r in rows]

    async def count_by_status(self, status: QueueStatus) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM task_queue WHERE status = ?",
                (status.value,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def count_completed_today(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM task_queue "
                "WHERE status = 'completed' AND date(completed_at) = date('now')",
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    # ── 执行历史 ──

    async def save_execution_record(self, record: ExecutionRecord):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO execution_history
                (id, task_id, task_name, status, started_at, completed_at,
                 duration_ms, triggered_by, output_url, output_summary,
                 error, published, publish_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record.id, record.task_id, record.task_name,
                record.status.value, record.started_at.isoformat(),
                record.completed_at.isoformat() if record.completed_at else None,
                record.duration_ms, record.triggered_by,
                record.output_url, record.output_summary, record.error,
                1 if record.published else 0, record.publish_url,
            ))
            await db.commit()

    async def get_execution_history(
        self, task_id: Optional[str] = None, limit: int = 50
    ) -> list[ExecutionRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if task_id:
                sql = "SELECT * FROM execution_history WHERE task_id = ? ORDER BY started_at DESC LIMIT ?"
                params = (task_id, limit)
            else:
                sql = "SELECT * FROM execution_history ORDER BY started_at DESC LIMIT ?"
                params = (limit,)
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_record(dict(r)) for r in rows]

    # ── 定时任务 CRUD ──

    async def save_scheduled_task(self, config: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO scheduled_tasks
                (id, name, description, enabled, trigger_type,
                 cron_expression, scheduled_at, timezone, human_readable,
                 generation_config, publish_config, tags,
                 created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                config['id'], config['name'], config.get('description'),
                1 if config.get('enabled', True) else 0,
                config['trigger']['type'],
                config['trigger'].get('cron_expression'),
                config['trigger'].get('scheduled_at'),
                config['trigger'].get('timezone', 'Asia/Shanghai'),
                config['trigger'].get('human_readable'),
                json.dumps(config['generation']),
                json.dumps(config.get('publish', {})),
                json.dumps(config.get('tags', [])),
                datetime.now().isoformat(), datetime.now().isoformat(),
            ))
            await db.commit()

    async def get_scheduled_tasks(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM scheduled_tasks ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_scheduled_task(self, task_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM scheduled_tasks WHERE id = ?", (task_id,)
            )
            await db.commit()

    # ── 内部转换 ──

    @staticmethod
    def _row_to_task(row: dict) -> BlogTask:
        return BlogTask(
            id=row['id'], name=row['name'],
            description=row['description'],
            trigger=TriggerConfig.model_validate_json(
                row['trigger_config']
            ),
            generation=BlogGenerationConfig.model_validate_json(
                row['generation_config']
            ),
            publish=PublishConfig.model_validate_json(
                row['publish_config']
            ),
            status=QueueStatus(row['status']),
            priority=row['priority'],
            queue_position=row['queue_position'],
            progress=row['progress'],
            current_stage=row['current_stage'] or '',
            stage_detail=row['stage_detail'] or '',
            output_url=row['output_url'],
            output_word_count=row['output_word_count'],
            output_image_count=row['output_image_count'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            tags=json.loads(row['tags'] or '[]'),
            user_id=row['user_id'],
        )

    @staticmethod
    def _row_to_record(row: dict) -> ExecutionRecord:
        return ExecutionRecord(
            id=row['id'], task_id=row['task_id'],
            task_name=row['task_name'],
            status=QueueStatus(row['status']),
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            duration_ms=row['duration_ms'],
            triggered_by=row['triggered_by'],
            output_url=row['output_url'],
            output_summary=row['output_summary'],
            error=row['error'],
            published=bool(row['published']),
            publish_url=row['publish_url'],
        )
