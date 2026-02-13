"""
37.04 重复查询检测与回滚保护

QueryDeduplicator — 按 Agent 隔离的查询缓存 + 连续回滚上限保护。
"""
import logging
from collections import OrderedDict
from typing import Dict

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONSECUTIVE_ROLLBACKS = 5
DEFAULT_MAX_CACHE_PER_AGENT = 1000


class QueryDeduplicator:
    """
    查询重复检测器。

    - 按 agent 隔离缓存（OrderedDict 实现 LRU 淘汰）
    - 连续回滚计数 + 上限保护
    """

    def __init__(
        self,
        max_consecutive_rollbacks: int = DEFAULT_MAX_CONSECUTIVE_ROLLBACKS,
        max_cache_per_agent: int = DEFAULT_MAX_CACHE_PER_AGENT,
    ):
        self._caches: Dict[str, OrderedDict] = {}
        self._max_rollbacks = max_consecutive_rollbacks
        self._max_cache = max_cache_per_agent
        self._consecutive_rollbacks = 0
        self._total_duplicates = 0

    @staticmethod
    def _normalize(query: str) -> str:
        return query.strip().lower()

    def is_duplicate(self, query: str, agent: str = "default") -> bool:
        """检查查询是否重复（不记录）"""
        key = self._normalize(query)
        cache = self._caches.get(agent)
        if cache and key in cache:
            self._total_duplicates += 1
            logger.debug(f"[QueryDedup] 重复查询: agent={agent}, query={query!r}")
            return True
        return False

    def record(self, query: str, agent: str = "default") -> None:
        """记录已执行的查询"""
        key = self._normalize(query)
        if agent not in self._caches:
            self._caches[agent] = OrderedDict()
        cache = self._caches[agent]
        cache[key] = True
        cache.move_to_end(key)
        # LRU 淘汰
        while len(cache) > self._max_cache:
            cache.popitem(last=False)

    def rollback(self) -> bool:
        """
        尝试回滚。

        Returns:
            True — 允许回滚（未达上限）
            False — 已达上限，拒绝回滚
        """
        if self._consecutive_rollbacks >= self._max_rollbacks:
            logger.warning(
                f"[QueryDedup] 连续回滚已达上限 ({self._max_rollbacks})，拒绝回滚"
            )
            return False
        self._consecutive_rollbacks += 1
        logger.info(
            f"[QueryDedup] 回滚 #{self._consecutive_rollbacks}/{self._max_rollbacks}"
        )
        return True

    def reset_rollback_count(self) -> None:
        """正常执行成功后重置连续回滚计数"""
        if self._consecutive_rollbacks > 0:
            logger.debug(
                f"[QueryDedup] 重置回滚计数 (was {self._consecutive_rollbacks})"
            )
        self._consecutive_rollbacks = 0

    def get_stats(self) -> Dict:
        total_queries = sum(len(c) for c in self._caches.values())
        return {
            "total_queries": total_queries,
            "total_duplicates": self._total_duplicates,
            "consecutive_rollbacks": self._consecutive_rollbacks,
            "max_consecutive_rollbacks": self._max_rollbacks,
            "agents": len(self._caches),
        }

    def clear(self) -> None:
        """清空所有缓存和计数"""
        self._caches.clear()
        self._consecutive_rollbacks = 0
        self._total_duplicates = 0
