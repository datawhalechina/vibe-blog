"""
safe_run — 优雅降级装饰器

用于增强型 Agent 节点（FactCheck、Humanizer、TextCleanup 等），
失败时自动跳过而不阻塞整个流水线。

用法：
    @safe_run(default_return={})
    def _factcheck_node(self, state):
        ...
"""

import functools
import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


def safe_run(
    default_return: Dict[str, Any] = None,
    log_prefix: str = "",
):
    """
    装饰器：Agent 节点优雅降级。

    异常时记录错误日志并返回 state（合并 default_return），
    不会阻塞后续节点。

    Args:
        default_return: 异常时写入 state 的默认值
        log_prefix: 日志前缀（默认取函数名）
    """
    if default_return is None:
        default_return = {}

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, state, *args, **kwargs):
            prefix = log_prefix or func.__name__
            try:
                return func(self, state, *args, **kwargs)
            except Exception as e:
                logger.error(f"[{prefix}] 异常，降级跳过: {e}")
                state.update(default_return)
                return state
        return wrapper
    return decorator
