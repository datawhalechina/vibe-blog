"""
子代理执行器（1002.13）

借鉴 DeerFlow SubagentExecutor 的双线程池设计，
在 ParallelTaskExecutor 的 TaskStatus/TaskResult 基础上
新增 Agent 级别的同步/异步执行能力。

关键差异：
- DeerFlow 使用 LangChain Agent SDK，vibe-blog 使用 AgentRunner
- 复用 ParallelTaskExecutor 的 TaskStatus/TaskResult 数据模型
- 通过 on_event 回调发送 SSE 事件
"""

import logging
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from services.blog_generator.parallel.executor import TaskResult, TaskStatus
from .config import SubagentConfig

logger = logging.getLogger(__name__)

# 全局后台任务存储（线程安全）
_background_tasks: Dict[str, TaskResult] = {}
_background_tasks_lock = threading.Lock()

# 双线程池：调度池 + 执行池
_scheduler_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="subagent-sched-")
_execution_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subagent-exec-")


class SubagentExecutor:
    """子代理执行器 — 支持同步和异步执行"""

    def __init__(
        self,
        config: SubagentConfig,
        llm_client: Any,
        on_event: Optional[Callable[[dict], None]] = None,
        trace_id: Optional[str] = None,
    ):
        self.config = config
        self.llm_client = llm_client
        self.on_event = on_event
        self.trace_id = trace_id or str(uuid.uuid4())[:8]

    def _emit(self, event: dict) -> None:
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                logger.warning(f"[trace={self.trace_id}] 事件回调失败: {e}")

    def execute(self, task_prompt: str) -> TaskResult:
        """同步执行子代理任务"""
        task_id = str(uuid.uuid4())[:8]
        result = TaskResult(
            task_id=task_id,
            task_name=self.config.name,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
        )
        try:
            messages = [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": task_prompt},
            ]
            response = self.llm_client.chat(messages=messages)
            result.result = response
            result.status = TaskStatus.COMPLETED
        except Exception as e:
            logger.error(f"[trace={self.trace_id}] 子代理 {self.config.name} 执行失败: {e}")
            result.status = TaskStatus.FAILED
            result.error = str(e)
        finally:
            result.completed_at = datetime.now()
            if result.started_at and result.completed_at:
                delta = result.completed_at - result.started_at
                result.duration_ms = int(delta.total_seconds() * 1000)
        return result

    def execute_async(self, task_prompt: str, task_id: Optional[str] = None) -> str:
        """异步执行 — 后台线程池调度 + 执行"""
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        result = TaskResult(
            task_id=task_id,
            task_name=self.config.name,
            status=TaskStatus.PENDING,
        )
        with _background_tasks_lock:
            _background_tasks[task_id] = result

        def run_task():
            with _background_tasks_lock:
                _background_tasks[task_id].status = TaskStatus.RUNNING
                _background_tasks[task_id].started_at = datetime.now()
            try:
                future: Future = _execution_pool.submit(self.execute, task_prompt)
                exec_result = future.result(timeout=self.config.timeout_seconds)
                with _background_tasks_lock:
                    _background_tasks[task_id].status = exec_result.status
                    _background_tasks[task_id].result = exec_result.result
                    _background_tasks[task_id].error = exec_result.error
                    _background_tasks[task_id].completed_at = datetime.now()
            except FuturesTimeoutError:
                with _background_tasks_lock:
                    _background_tasks[task_id].status = TaskStatus.TIMED_OUT
                    _background_tasks[task_id].error = f"超时 ({self.config.timeout_seconds}s)"
                    _background_tasks[task_id].completed_at = datetime.now()
            except Exception as e:
                with _background_tasks_lock:
                    _background_tasks[task_id].status = TaskStatus.FAILED
                    _background_tasks[task_id].error = str(e)
                    _background_tasks[task_id].completed_at = datetime.now()
            finally:
                with _background_tasks_lock:
                    status = _background_tasks[task_id].status.value
                self._emit({
                    "type": "subtask_completed",
                    "task_id": task_id,
                    "status": status,
                })

        _scheduler_pool.submit(run_task)
        return task_id


def get_background_task(task_id: str) -> Optional[TaskResult]:
    """查询后台任务状态"""
    with _background_tasks_lock:
        return _background_tasks.get(task_id)
