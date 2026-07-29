"""
SSE 任务管理服务 - 提供实时进度推送
复用自 AI 绘本项目
"""
import json
import time
import logging
import uuid
from queue import Queue, Empty
from threading import Thread, Lock
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled", "canceled"}
ACTIVE_CLEANUP_RETRY_SECONDS = 60
MAX_TASK_INACTIVITY_SECONDS = 24 * 60 * 60


@dataclass
class TaskProgress:
    """任务进度数据"""
    task_id: str
    status: str = "pending"  # pending, running, completed, failed, cancelled
    current_stage: str = ""
    stage_progress: int = 0
    overall_progress: int = 0
    message: str = ""
    results: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class TaskManager:
    """任务管理器 - 管理任务状态和 SSE 消息队列"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tasks: Dict[str, TaskProgress] = {}
        self.queues: Dict[str, Queue] = {}
        self._cleanup_tasks = set()
        self.task_lock = Lock()
        logger.info("TaskManager 初始化完成")
    
    def create_task(self, task_id: str = None, task_type: str = None) -> str:
        """创建新任务
        
        Args:
            task_id: 可选，自定义任务 ID，不传则自动生成
            task_type: 可选，任务类型标识
        """
        if not task_id:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_id = f"task_{ts}_{uuid.uuid4().hex[:8]}"
        with self.task_lock:
            self.tasks[task_id] = TaskProgress(
                task_id=task_id,
                status="pending"
            )
            self.queues[task_id] = Queue()
        logger.info(f"创建任务: {task_id}" + (f" (类型: {task_type})" if task_type else ""))
        return task_id
    
    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def get_queue(self, task_id: str) -> Optional[Queue]:
        """获取任务消息队列"""
        return self.queues.get(task_id)
    
    def send_event(self, task_id: str, event: str, data: Dict[str, Any]):
        """发送 SSE 事件（带唯一 ID 和时间戳）"""
        payload = {
            'event': event,
            'id': uuid.uuid4().hex[:12],
            'timestamp': time.time(),
            'data': data,
        }
        queue_found = False
        with self.task_lock:
            task = self.tasks.get(task_id)
            if task and task.status in {"pending", "running"}:
                if event == "complete":
                    task.status = "completed"
                    task.overall_progress = 100
                    task.outputs = data.get("outputs", data)
                    task.updated_at = datetime.utcnow()
                elif event == "error":
                    task.error = data.get("message") or "任务失败"
                    if not data.get("recoverable", False):
                        task.status = "failed"
                    task.updated_at = datetime.utcnow()
                elif event == "cancelled":
                    task.status = "cancelled"
                    task.updated_at = datetime.utcnow()

            queue = self.queues.get(task_id)
            if queue:
                queue.put(payload)
                queue_found = True

        if queue_found:
            if event not in ('writing_chunk', 'log', 'stream'):
                logger.debug(f"SSE 事件已入队 [{task_id}]: {event}")
        else:
            # 队列不存在时只记录一次 warning，避免日志洪泛
            warn_key = f"_sse_warn_{task_id}"
            if not getattr(self, warn_key, False):
                setattr(self, warn_key, True)
                logger.warning(f"SSE 队列不存在 [{task_id}]，后续同任务事件将静默丢弃")
    
    def send_progress(self, task_id: str, stage: str, progress: int, message: str, **extra):
        """发送进度更新"""
        task = self.tasks.get(task_id)
        if task:
            task.current_stage = stage
            task.stage_progress = progress
            task.message = message
            task.updated_at = datetime.utcnow()
            
            # 计算总体进度
            stage_weights = {
                'analyze': 10,
                'metaphor': 15,
                'outline': 20,
                'content': 30,
                'image': 25
            }
            completed_weight = sum(
                w for s, w in stage_weights.items() 
                if s in task.results and task.results[s].get('completed')
            )
            current_weight = stage_weights.get(stage, 0) * progress / 100
            task.overall_progress = int(completed_weight + current_weight)
        
        self.send_event(task_id, 'progress', {
            'stage': stage,
            'progress': progress,
            'message': message,
            'overall_progress': task.overall_progress if task else 0,
            **extra
        })
    
    def send_stream(self, task_id: str, stage: str, delta: str, accumulated: str):
        """发送流式内容"""
        self.send_event(task_id, 'stream', {
            'stage': stage,
            'delta': delta,
            'accumulated': accumulated
        })
    
    def send_result(self, task_id: str, stage: str, result_type: str, data: Dict[str, Any]):
        """发送中间结果"""
        task = self.tasks.get(task_id)
        if task:
            if stage not in task.results:
                task.results[stage] = {}
            task.results[stage]['completed'] = True
            task.results[stage]['data'] = data
            task.updated_at = datetime.utcnow()
        
        self.send_event(task_id, 'result', {
            'stage': stage,
            'type': result_type,
            'data': data
        })
    
    def send_complete(self, task_id: str, outputs: Dict[str, Any]):
        """发送完成事件"""
        self.send_event(task_id, 'complete', {
            'task_id': task_id,
            'status': 'completed',
            'outputs': outputs
        })
    
    def send_error(self, task_id: str, stage: str, message: str, recoverable: bool = False, **extra):
        """发送错误事件"""
        self.send_event(task_id, 'error', {
            'stage': stage,
            'message': message,
            'recoverable': recoverable,
            **extra
        })
    
    def set_running(self, task_id: str):
        """设置任务为运行中"""
        task = self.tasks.get(task_id)
        if task:
            task.status = "running"
            task.updated_at = datetime.utcnow()
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status in ("running", "pending"):
            self.send_event(task_id, 'cancelled', {'task_id': task_id, 'message': '任务已取消'})
            if task.status == "cancelled":
                logger.info(f"任务已取消: {task_id}")
                return True
        return False
    
    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否已取消"""
        task = self.tasks.get(task_id)
        return task is not None and task.status == "cancelled"
    
    def cleanup_task(self, task_id: str, delay: int = 300):
        """延迟清理任务；活跃任务保留，失联任务最终回收。"""
        with self.task_lock:
            if task_id in self._cleanup_tasks:
                return
            self._cleanup_tasks.add(task_id)

        def _cleanup():
            next_delay = max(delay, 0)
            try:
                while True:
                    time.sleep(next_delay)
                    removed_reason = None
                    with self.task_lock:
                        task = self.tasks.get(task_id)
                        if task is None:
                            self.queues.pop(task_id, None)
                            return

                        inactive_seconds = (
                            datetime.utcnow() - task.updated_at
                        ).total_seconds()
                        if task.status in TERMINAL_TASK_STATUSES:
                            removed_reason = "terminal"
                        elif inactive_seconds >= MAX_TASK_INACTIVITY_SECONDS:
                            removed_reason = "stale"

                        if removed_reason:
                            self.tasks.pop(task_id, None)
                            self.queues.pop(task_id, None)
                        else:
                            remaining = MAX_TASK_INACTIVITY_SECONDS - inactive_seconds
                            next_delay = min(
                                ACTIVE_CLEANUP_RETRY_SECONDS,
                                max(remaining, 1),
                            )

                    if removed_reason:
                        if removed_reason == "stale":
                            logger.warning(f"清理失联任务: {task_id}")
                        else:
                            logger.info(f"清理任务: {task_id}")
                        return
            finally:
                with self.task_lock:
                    self._cleanup_tasks.discard(task_id)
        
        Thread(target=_cleanup, daemon=True).start()


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
