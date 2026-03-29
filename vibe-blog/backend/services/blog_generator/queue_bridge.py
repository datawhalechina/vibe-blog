"""
TaskQueueManager 桥接 — 生成过程中同步进度/状态到排队系统
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_queue_manager():
    """获取 queue_manager 实例，失败返回 None"""
    try:
        from flask import current_app
        return getattr(current_app._get_current_object(), 'queue_manager', None)
    except Exception:
        return None


def _run(coro):
    """在同步上下文中运行异步协程"""
    return asyncio.run(coro)


def update_queue_progress(
    task_id: str,
    progress: int,
    stage: str = "",
    detail: str = "",
):
    """
    更新任务进度到排队系统（供 Dashboard 进度条展示）。

    Args:
        task_id: 任务 ID
        progress: 进度百分比 0-100
        stage: 当前阶段名称
        detail: 阶段详情
    """
    try:
        qm = _get_queue_manager()
        if not qm:
            return

        async def _update():
            await qm.update_progress(task_id, progress, stage, detail)

        _run(_update())
    except Exception as e:
        logger.debug(f"更新进度失败: {e}")


def update_queue_status(
    task_id: str,
    status: str,
    word_count: int = 0,
    image_count: int = 0,
    error_msg: str = "",
):
    """
    更新任务最终状态到排队系统。

    Args:
        task_id: 任务 ID
        status: "completed" 或 "failed"
        word_count: 字数（仅 completed 时有意义）
        image_count: 图片数（仅 completed 时有意义）
        error_msg: 错误信息（仅 failed 时有意义）
    """
    try:
        qm = _get_queue_manager()
        if not qm:
            return

        from services.task_queue.models import QueueStatus

        async def _update():
            task = await qm.db.get_task(task_id)
            if not task:
                logger.warning(f"[QueueBridge] 任务 {task_id} 不存在，跳过状态更新")
                return
            task.status = QueueStatus(status)
            task.completed_at = datetime.now()
            task.progress = 100 if status == "completed" else task.progress
            if status == "completed":
                task.output_word_count = word_count
                task.output_image_count = image_count
                task.current_stage = "done"
            else:
                task.current_stage = "failed"
                task.stage_detail = error_msg[:200] if error_msg else "unknown"
            await qm.db.save_task(task)
            logger.info(f"[QueueBridge] 任务 {task_id} 状态更新: {status}")

        _run(_update())
    except Exception as e:
        logger.warning(f"[QueueBridge] 更新状态失败 ({task_id} → {status}): {e}")
