"""
TaskQueueManager 桥接 — 生成完成/失败时更新排队系统记录
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def update_queue_status(
    task_id: str,
    status: str,
    word_count: int = 0,
    image_count: int = 0,
    error_msg: str = "",
):
    """
    更新 TaskQueueManager 中的任务状态（非关键路径，失败不影响主流程）。

    Args:
        task_id: 任务 ID
        status: "completed" 或 "failed"
        word_count: 字数（仅 completed 时有意义）
        image_count: 图片数（仅 completed 时有意义）
        error_msg: 错误信息（仅 failed 时有意义）
    """
    try:
        from flask import current_app
        queue_manager = getattr(current_app._get_current_object(), 'queue_manager', None)
        if not queue_manager:
            return

        from services.task_queue.models import QueueStatus

        async def _update():
            task = await queue_manager.db.get_task(task_id)
            if not task:
                return
            task.status = QueueStatus(status)
            task.completed_at = datetime.now()
            task.progress = 100 if status == "completed" else task.progress
            if status == "completed":
                task.output_word_count = word_count
                task.output_image_count = image_count
                task.current_stage = "done"
            else:
                task.stage_detail = error_msg[:200] if error_msg else "unknown"
            await queue_manager.db.save_task(task)

        asyncio.run(_update())
    except Exception as e:
        logger.debug(f"更新排队系统状态失败 (非关键): {e}")
