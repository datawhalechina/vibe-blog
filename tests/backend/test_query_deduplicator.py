"""
37.04 重复查询检测与回滚保护 — 单元测试
"""
import pytest
from utils.query_deduplicator import QueryDeduplicator


class TestIsDuplicate:
    """查询重复检测"""

    def test_first_query_not_duplicate(self):
        d = QueryDeduplicator()
        assert d.is_duplicate("hello", "agent_a") is False

    def test_same_query_same_agent_is_duplicate(self):
        d = QueryDeduplicator()
        d.record("hello", "agent_a")
        assert d.is_duplicate("hello", "agent_a") is True

    def test_same_query_different_agent_not_duplicate(self):
        d = QueryDeduplicator()
        d.record("hello", "agent_a")
        assert d.is_duplicate("hello", "agent_b") is False

    def test_normalize_strips_and_lowercases(self):
        d = QueryDeduplicator()
        d.record("  Hello World  ", "a")
        assert d.is_duplicate("hello world", "a") is True

    def test_different_query_not_duplicate(self):
        d = QueryDeduplicator()
        d.record("hello", "a")
        assert d.is_duplicate("world", "a") is False


class TestRecord:
    """记录查询"""

    def test_record_makes_query_duplicate(self):
        d = QueryDeduplicator()
        d.record("q1", "a")
        assert d.is_duplicate("q1", "a") is True

    def test_record_multiple_agents(self):
        d = QueryDeduplicator()
        d.record("q1", "a")
        d.record("q2", "b")
        assert d.is_duplicate("q1", "a") is True
        assert d.is_duplicate("q2", "b") is True
        assert d.is_duplicate("q1", "b") is False


class TestLRUEviction:
    """LRU 淘汰"""

    def test_eviction_at_max_cache_size(self):
        d = QueryDeduplicator(max_cache_per_agent=3)
        d.record("q1", "a")
        d.record("q2", "a")
        d.record("q3", "a")
        d.record("q4", "a")  # q1 should be evicted
        assert d.is_duplicate("q1", "a") is False
        assert d.is_duplicate("q4", "a") is True


class TestRollback:
    """回滚保护"""

    def test_rollback_allowed_initially(self):
        d = QueryDeduplicator(max_consecutive_rollbacks=5)
        assert d.rollback() is True

    def test_rollback_increments_count(self):
        d = QueryDeduplicator(max_consecutive_rollbacks=3)
        assert d.rollback() is True
        assert d.rollback() is True
        assert d.rollback() is True
        # 第 4 次超限
        assert d.rollback() is False

    def test_reset_rollback_count(self):
        d = QueryDeduplicator(max_consecutive_rollbacks=2)
        d.rollback()
        d.rollback()
        assert d.rollback() is False
        d.reset_rollback_count()
        assert d.rollback() is True

    def test_rollback_returns_false_at_limit(self):
        d = QueryDeduplicator(max_consecutive_rollbacks=1)
        assert d.rollback() is True
        assert d.rollback() is False
        assert d.rollback() is False


class TestGetStats:
    """统计信息"""

    def test_stats_empty(self):
        d = QueryDeduplicator()
        stats = d.get_stats()
        assert stats["total_queries"] == 0
        assert stats["total_duplicates"] == 0
        assert stats["consecutive_rollbacks"] == 0

    def test_stats_after_operations(self):
        d = QueryDeduplicator()
        d.record("q1", "a")
        d.record("q2", "a")
        d.record("q3", "b")
        # 触发一次重复检测
        d.is_duplicate("q1", "a")  # duplicate
        d.is_duplicate("q99", "a")  # not duplicate
        stats = d.get_stats()
        assert stats["total_queries"] == 3
        assert stats["total_duplicates"] == 1
        assert stats["agents"] == 2


class TestClear:
    """清空缓存"""

    def test_clear_resets_all(self):
        d = QueryDeduplicator()
        d.record("q1", "a")
        d.rollback()
        d.clear()
        assert d.is_duplicate("q1", "a") is False
        stats = d.get_stats()
        assert stats["total_queries"] == 0
        assert stats["consecutive_rollbacks"] == 0
