"""
子代理委托入口函数（1002.13）

供 generator.py 管线节点调用，封装子代理查找、
执行和 SSE 事件发送的完整流程。
"""

import logging
import uuid
from typing import Any, Callable, Dict, Optional

from .registry import get_subagent_config
from .executor import SubagentExecutor
from services.blog_generator.parallel.executor import TaskStatus

logger = logging.getLogger(__name__)


def delegate_task(
    subagent_name: str,
    task_prompt: str,
    llm_client: Any,
    on_event: Optional[Callable[[dict], None]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    委托任务给指定子代理（同步执行）。

    Args:
        subagent_name: 子代理名称（需已注册）
        task_prompt: 任务提示词
        llm_client: LLM 客户端
        on_event: SSE 事件回调
        trace_id: 分布式追踪 ID

    Returns:
        dict with keys: status, result, error, task_id, trace_id
    """
    trace_id = trace_id or str(uuid.uuid4())[:8]

    config = get_subagent_config(subagent_name)
    if config is None:
        error_msg = f"子代理未找到: {subagent_name}"
        logger.error(f"[trace={trace_id}] {error_msg}")
        return {
            "status": "failed",
            "result": None,
            "error": error_msg,
            "task_id": None,
            "trace_id": trace_id,
        }

    # 发送 subtask_started 事件
    if on_event:
        on_event({
            "type": "subtask_started",
            "subagent": subagent_name,
            "trace_id": trace_id,
        })

    executor = SubagentExecutor(
        config=config,
        llm_client=llm_client,
        on_event=on_event,
        trace_id=trace_id,
    )

    result = executor.execute(task_prompt)

    # 发送 subtask_completed 事件
    if on_event:
        on_event({
            "type": "subtask_completed",
            "subagent": subagent_name,
            "task_id": result.task_id,
            "status": result.status.value,
            "trace_id": trace_id,
        })

    return {
        "status": result.status.value,
        "result": result.result,
        "error": result.error,
        "task_id": result.task_id,
        "trace_id": trace_id,
    }
