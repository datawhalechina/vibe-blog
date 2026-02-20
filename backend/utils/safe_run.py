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
import time
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


def safe_run(
    default_return: Dict[str, Any] = None,
    log_prefix: str = "",
    max_retries: int = 0,
    retry_delay: float = 1.0,
):
    """
    装饰器：Agent 节点优雅降级。

    异常时记录错误日志并返回 state（合并 default_return），
    不会阻塞后续节点。

    Args:
        default_return: 异常时写入 state 的默认值
        log_prefix: 日志前缀（默认取函数名）
        max_retries: 最大重试次数（0 = 不重试，保持向后兼容）
        retry_delay: 首次重试延迟秒数（指数退避）
    """
    if default_return is None:
        default_return = {}

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, state, *args, **kwargs):
            prefix = log_prefix or func.__name__
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(self, state, *args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        delay = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"[{prefix}] 第 {attempt + 1}/{max_retries + 1} 次失败: {e}，"
                            f"{delay:.1f}s 后重试"
                        )
                        time.sleep(delay)
            logger.error(f"[{prefix}] 异常，降级跳过: {last_error}")
            state.update(default_return)
            return state
        return wrapper
    return decorator
