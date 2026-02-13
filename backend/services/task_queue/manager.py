"""
TaskQueueManager — 排队引擎 + Worker + 事件系统

功能：
- asyncio.PriorityQueue 内存排队（优先级 + FIFO）
- asyncio.Semaphore 并发控制
- SQLite 持久化
- 事件回调系统（SSE 桥接）
"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

from .db import TaskDB
from .models import BlogTask, ExecutionRecord, QueueStatus

logger = logging.getLogger(__name__)


class TaskQueueManager:
    def __init__(self, db_path: str = "data/task_queue.db",
                 max_concurrent: int = 2):
        self.db = TaskDB(db_path)
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._callbacks: dict[str, list[Callable]] = {
            'task_queued': [],
            'task_started': [],
            'task_progress': [],
            'task_completed': [],
            'task_failed': [],
            'task_cancelled': [],
        }
        self._worker_task: Optional[asyncio.Task] = None
        self._blog_generator = None

    async def init(self):
        """初始化数据库 + 恢复未完成任务"""
        await self.db.init()
        await self._recover_queued_tasks()

    def set_blog_generator(self, generator):
        self._blog_generator = generator

    # ── 公开 API ──

    async def enqueue(self, task: BlogTask) -> str:
        """入队，返回 task_id"""
        queued_count = await self.db.count_by_status(QueueStatus.QUEUED)
        task.queue_position = queued_count + 1
        await self.db.save_task(task)
        await self._queue.put((
            -task.priority.value,
            task.created_at.timestamp(),
            task.id,
        ))
        await self._emit('task_queued', task)
        logger.info(
            f"[Queue] 入队: {task.id} '{task.name}' "
            f"(位置 #{task.queue_position})"
        )
        return task.id

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        task = await self.db.get_task(task_id)
        if not task:
            return False
        if task.status not in (QueueStatus.QUEUED, QueueStatus.RUNNING):
            return False
        task.status = QueueStatus.CANCELLED
        task.updated_at = datetime.now()
        task.completed_at = datetime.now()
        await self.db.save_task(task)
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
        await self._emit('task_cancelled', task)
        logger.info(f"[Queue] 已取消: {task_id}")
        return True

    async def get_task(self, task_id: str) -> Optional[BlogTask]:
        return await self.db.get_task(task_id)

    async def get_queue_snapshot(self) -> dict:
        """Dashboard 用的队列快照"""
        return {
            'queued': [t.model_dump() for t in
                       await self.db.get_tasks_by_status(QueueStatus.QUEUED)],
            'running': [t.model_dump() for t in
                        await self.db.get_tasks_by_status(QueueStatus.RUNNING)],
            'completed': [t.model_dump() for t in
                          await self.db.get_tasks_by_status(
                              QueueStatus.COMPLETED, limit=20)],
            'failed': [t.model_dump() for t in
                       await self.db.get_tasks_by_status(
                           QueueStatus.FAILED, limit=10)],
            'cancelled': [t.model_dump() for t in
                          await self.db.get_tasks_by_status(
                              QueueStatus.CANCELLED, limit=10)],
            'stats': {
                'queued_count': await self.db.count_by_status(
                    QueueStatus.QUEUED),
                'running_count': await self.db.count_by_status(
                    QueueStatus.RUNNING),
                'completed_today': await self.db.count_completed_today(),
                'failed_count': await self.db.count_by_status(
                    QueueStatus.FAILED),
                'cancelled_count': await self.db.count_by_status(
                    QueueStatus.CANCELLED),
                'max_concurrent': self.max_concurrent,
            },
        }

    async def update_progress(self, task_id: str, progress: int,
                              stage: str = "", detail: str = ""):
        task = await self.db.get_task(task_id)
        if task and task.status == QueueStatus.RUNNING:
            task.progress = progress
            task.current_stage = stage
            task.stage_detail = detail
            task.updated_at = datetime.now()
            await self.db.save_task(task)
            await self._emit('task_progress', task)

    # ── Worker ──

    async def start_worker(self):
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(
            f"[Queue] Worker 已启动 "
            f"(max_concurrent={self.max_concurrent})"
        )

    async def stop_worker(self):
        if self._worker_task:
            self._worker_task.cancel()

    async def _worker_loop(self):
        while True:
            try:
                _, _, task_id = await self._queue.get()
                await self._semaphore.acquire()
                task = await self.db.get_task(task_id)
                if not task or task.status == QueueStatus.CANCELLED:
                    self._semaphore.release()
                    continue
                exec_task = asyncio.create_task(
                    self._execute_task(task_id)
                )
                self._running_tasks[task_id] = exec_task
                exec_task.add_done_callback(
                    lambda t, tid=task_id:
                        self._running_tasks.pop(tid, None)
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Queue] Worker 异常: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task_id: str):
        task = await self.db.get_task(task_id)
        if not task:
            self._semaphore.release()
            return
        start_time = datetime.now()
        try:
            task.status = QueueStatus.RUNNING
            task.started_at = start_time
            task.progress = 0
            await self.db.save_task(task)
            await self._emit('task_started', task)
            result = await self._run_blog_generation(task)
            task.status = QueueStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100
            if result:
                task.output_url = result.get('url')
                task.output_word_count = result.get('word_count')
                task.output_image_count = result.get('image_count')
            await self.db.save_task(task)
            duration = int(
                (task.completed_at - start_time).total_seconds() * 1000
            )
            await self.db.save_execution_record(ExecutionRecord(
                task_id=task.id, task_name=task.name,
                status=QueueStatus.COMPLETED,
                started_at=start_time,
                completed_at=task.completed_at,
                duration_ms=duration,
                triggered_by=task.trigger.type.value,
                output_url=task.output_url,
            ))
            await self._emit('task_completed', task)
        except asyncio.CancelledError:
            task.status = QueueStatus.CANCELLED
            task.completed_at = datetime.now()
            await self.db.save_task(task)
        except Exception as e:
            task.status = QueueStatus.FAILED
            task.completed_at = datetime.now()
            await self.db.save_task(task)
            duration = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            await self.db.save_execution_record(ExecutionRecord(
                task_id=task.id, task_name=task.name,
                status=QueueStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=duration,
                triggered_by=task.trigger.type.value,
                error=str(e),
            ))
            await self._emit('task_failed', task)
            logger.error(f"[Queue] 失败: {task_id} - {e}")
        finally:
            self._semaphore.release()

    async def _run_blog_generation(self, task: BlogTask) -> dict | None:
        if not self._blog_generator:
            raise RuntimeError("BlogGenerator 未注入")
        config = {
            'topic': task.generation.topic,
            'article_type': task.generation.article_type,
            'target_length': task.generation.target_length,
            'image_style': task.generation.image_style,
        }

        async def progress_callback(progress, stage, detail=""):
            await self.update_progress(task.id, progress, stage, detail)

        return await self._blog_generator.generate(
            config=config, progress_callback=progress_callback,
        )

    # ── 恢复 ──

    async def _recover_queued_tasks(self):
        queued = await self.db.get_tasks_by_status(QueueStatus.QUEUED)
        running = await self.db.get_tasks_by_status(QueueStatus.RUNNING)

        # RUNNING 状态的任务在重启后标记为 FAILED（线程已丢失，无法恢复）
        for task in running:
            task.status = QueueStatus.FAILED
            task.completed_at = datetime.now()
            task.stage_detail = "服务重启，任务中断"
            await self.db.save_task(task)
            logger.warning(
                f"[Queue] 标记中断任务为失败: {task.id} '{task.name}'"
            )

        # QUEUED 状态的任务也标记为 FAILED（无 worker 消费）
        for task in queued:
            task.status = QueueStatus.FAILED
            task.completed_at = datetime.now()
            task.stage_detail = "服务重启，排队任务已清理"
            await self.db.save_task(task)

        total = len(running) + len(queued)
        if total:
            logger.info(
                f"[Queue] 清理 {total} 个残留任务 "
                f"(running={len(running)}, queued={len(queued)})"
            )

    # ── 事件系统 ──

    def on(self, event: str, callback: Callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    async def _emit(self, event: str, task: BlogTask):
        for cb in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(task)
                else:
                    cb(task)
            except Exception as e:
                logger.error(
                    f"[Queue] 事件回调异常 ({event}): {e}"
                )
