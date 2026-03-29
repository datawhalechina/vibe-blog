"""
统一并行任务执行引擎（102.01）

借鉴 DeerFlow SubagentExecutor 的设计，替换 generator.py 中散落的
ad-hoc ThreadPoolExecutor 模式，提供统一的超时保护、状态追踪、
串行/并行自动切换和错误处理。
"""

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .config import TaskConfig

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass
class TaskResult:
    """并行任务执行结果"""
    task_id: str
    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    @property
    def success(self) -> bool:
        return self.status == TaskStatus.COMPLETED


class ParallelTaskExecutor:
    """
    统一并行任务执行引擎

    借鉴 DeerFlow SubagentExecutor 的设计：
    - 统一的超时保护
    - 统一的状态追踪（TaskResult）
    - 串行/并行自动切换（TRACE_ENABLED）
    - 统一的错误处理和隔离
    - 可选 SSE 事件回调
    """

    def __init__(
        self,
        max_workers: int = None,
        default_timeout: int = 300,
        on_task_event: Callable[[dict], None] = None,
        enable_parallel: bool = True,
    ):
        self.max_workers = max_workers or int(
            os.environ.get("BLOG_GENERATOR_MAX_WORKERS", "3")
        )
        self.default_timeout = default_timeout
        self.on_task_event = on_task_event
        self._use_parallel = enable_parallel
        if self._use_parallel and self.max_workers < 3:
            self.max_workers = 3

    def run_parallel(
        self,
        tasks: List[Dict[str, Any]],
        config: TaskConfig = None,
    ) -> List[TaskResult]:
        """
        执行一组任务（自动选择并行/串行）。

        Args:
            tasks: 任务列表，每个任务是 dict:
                - "id": 任务 ID（可选，自动生成）
                - "name": 任务名称
                - "fn": Callable，执行函数
                - "args": tuple，位置参数（可选）
                - "kwargs": dict，关键字参数（可选）
            config: 任务配置（可选）

        Returns:
            TaskResult 列表，顺序与输入 tasks 一致
        """
        if not tasks:
            return []

        config = config or TaskConfig(name="parallel_batch")
        timeout = config.timeout_seconds or self.default_timeout

        # 初始化结果列表
        results: List[TaskResult] = []
        for task in tasks:
            task_id = task.get("id", str(uuid.uuid4())[:8])
            results.append(TaskResult(
                task_id=task_id,
                task_name=task.get("name", config.name),
                status=TaskStatus.PENDING,
            ))

        if self._use_parallel and len(tasks) > 1:
            self._execute_parallel(tasks, results, timeout)
        else:
            self._execute_serial(tasks, results, timeout)

        return results

    def _execute_parallel(
        self,
        tasks: List[Dict],
        results: List[TaskResult],
        timeout: int,
    ):
        """并行执行 -- 确保 executor 生命周期安全"""
        workers = min(self.max_workers, len(tasks))
        logger.info(f"并行执行 {len(tasks)} 个任务，使用 {workers} 个线程")

        self._emit_event("batch_started", {
            "total": len(tasks),
            "workers": workers,
        })

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {}
            for idx, task in enumerate(tasks):
                results[idx].status = TaskStatus.RUNNING
                results[idx].started_at = datetime.now()

                fn = task["fn"]
                args = task.get("args", ())
                kwargs = task.get("kwargs", {})

                future = executor.submit(fn, *args, **kwargs)
                future_to_idx[future] = idx

            # 关键：在 with 块内完成所有 future 收集
            try:
                for future in as_completed(future_to_idx, timeout=timeout):
                    idx = future_to_idx[future]
                    try:
                        results[idx].result = future.result(timeout=0)
                        results[idx].status = TaskStatus.COMPLETED
                    except TimeoutError:
                        results[idx].status = TaskStatus.TIMED_OUT
                        results[idx].error = "任务超时"
                        logger.error(f"任务超时: {results[idx].task_name}")
                    except Exception as e:
                        results[idx].status = TaskStatus.FAILED
                        results[idx].error = str(e)
                        logger.error(f"任务失败: {results[idx].task_name}: {e}")
                    finally:
                        results[idx].completed_at = datetime.now()
                        self._calc_duration(results[idx])
                        self._emit_event("task_completed", {
                            "task_id": results[idx].task_id,
                            "task_name": results[idx].task_name,
                            "status": results[idx].status.value,
                        })
            except TimeoutError:
                # as_completed 超时：标记未完成的任务并取消 future
                for future, idx in future_to_idx.items():
                    if results[idx].status == TaskStatus.RUNNING:
                        results[idx].status = TaskStatus.TIMED_OUT
                        results[idx].error = f"任务超时 ({timeout}s)"
                        results[idx].completed_at = datetime.now()
                        self._calc_duration(results[idx])
                        logger.error(f"任务超时: {results[idx].task_name}")
                        future.cancel()  # 取消未完成的 future

        # with 块退出后 executor 已 shutdown，不再引用任何 future
        self._emit_batch_completed(results)

    def _execute_serial(
        self,
        tasks: List[Dict],
        results: List[TaskResult],
        timeout: int,
    ):
        """串行执行（追踪模式或单任务）"""
        mode = "串行（追踪模式）" if not self._use_parallel else "串行（单任务）"
        logger.info(f"{mode}执行 {len(tasks)} 个任务")

        for idx, task in enumerate(tasks):
            results[idx].status = TaskStatus.RUNNING
            results[idx].started_at = datetime.now()

            fn = task["fn"]
            args = task.get("args", ())
            kwargs = task.get("kwargs", {})

            try:
                result_value = fn(*args, **kwargs)
                results[idx].status = TaskStatus.COMPLETED
                results[idx].result = result_value
            except Exception as e:
                results[idx].status = TaskStatus.FAILED
                results[idx].error = str(e)
                logger.error(f"任务失败: {results[idx].task_name}: {e}")
            finally:
                results[idx].completed_at = datetime.now()
                self._calc_duration(results[idx])

    @staticmethod
    def _calc_duration(task_result: TaskResult):
        if task_result.started_at and task_result.completed_at:
            delta = task_result.completed_at - task_result.started_at
            task_result.duration_ms = int(delta.total_seconds() * 1000)

    def _emit_event(self, event_type: str, data: dict):
        """发送 SSE 事件"""
        if self.on_task_event:
            try:
                self.on_task_event({"type": event_type, **data})
            except Exception as e:
                logger.warning(f"SSE 事件发送失败: {e}")

    def _emit_batch_completed(self, results: List[TaskResult]):
        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded
        total_ms = sum(r.duration_ms or 0 for r in results)
        self._emit_event("batch_completed", {
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "duration_ms": total_ms,
        })
