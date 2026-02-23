"""
子代理并发限制守卫（1002.13）

借鉴 DeerFlow SubagentLimitMiddleware，
使用信号量控制同时运行的子代理数量。
超额任务排队等待（而非截断）。
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

MAX_CONCURRENT_SUBAGENTS = 3


class SubagentLimitGuard:
    """并发限制守卫 — 信号量控制子代理并发数"""

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_SUBAGENTS):
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active = 0
        self._lock = threading.Lock()

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """获取执行许可，超时返回 False"""
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._active += 1
        return acquired

    def release(self) -> None:
        """释放执行许可"""
        with self._lock:
            self._active = max(0, self._active - 1)
        self._semaphore.release()
