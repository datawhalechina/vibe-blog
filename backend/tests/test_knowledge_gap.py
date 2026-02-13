"""
75.04 知识空白检测与多轮搜索 — 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.services.knowledge_gap_detector import (
    KnowledgeGapDetector,
    MAX_SEARCH_ROUNDS,
)
from services.blog_generator.services.multi_round_searcher import MultiRoundSearcher


# ---------------------------------------------------------------------------
# KnowledgeGapDetector
# ---------------------------------------------------------------------------

class TestKnowledgeGapDetector:

    def test_max_rounds_config(self):
        assert MAX_SEARCH_ROUNDS["short"] == 3
        assert MAX_SEARCH_ROUNDS["medium"] == 5
        assert MAX_SEARCH_ROUNDS["long"] == 8

    def test_should_continue_within_limit(self):
        detector = KnowledgeGapDetector(llm_service=None)
        gaps = [{"gap": "缺少X", "refined_query": "X 详解"}]
        assert detector.should_continue(gaps, current_round=1, max_rounds=5) is True

    def test_should_continue_at_limit(self):
        detector = KnowledgeGapDetector(llm_service=None)
        gaps = [{"gap": "缺少X", "refined_query": "X 详解"}]
        assert detector.should_continue(gaps, current_round=5, max_rounds=5) is False

    def test_should_continue_no_gaps(self):
        detector = KnowledgeGapDetector(llm_service=None)
        assert detector.should_continue([], current_round=1, max_rounds=5) is False

    def test_detect_without_llm_returns_empty(self):
        """无 LLM 时返回空列表"""
        detector = KnowledgeGapDetector(llm_service=None)
        result = detector.detect(
            search_results=[{"title": "A", "snippet": "content"}],
            topic="AI",
        )
        assert result == []

    def test_detect_with_llm_parses_json(self):
        """LLM 返回 JSON 时正确解析"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = '[{"gap": "缺少 Transformer 原理", "refined_query": "Transformer 注意力机制 原理"}]'
        detector = KnowledgeGapDetector(llm_service=mock_llm)
        result = detector.detect(
            search_results=[{"title": "A", "snippet": "content"}],
            topic="Transformer",
        )
        assert len(result) == 1
        assert result[0]["gap"] == "缺少 Transformer 原理"
        assert "refined_query" in result[0]

    def test_detect_with_llm_invalid_json(self):
        """LLM 返回非 JSON 时返回空列表"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "这不是 JSON"
        detector = KnowledgeGapDetector(llm_service=mock_llm)
        result = detector.detect(
            search_results=[{"title": "A", "snippet": "content"}],
            topic="AI",
        )
        assert result == []

    def test_detect_with_llm_returns_none(self):
        """LLM 返回 None 时返回空列表"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = None
        detector = KnowledgeGapDetector(llm_service=mock_llm)
        result = detector.detect(
            search_results=[{"title": "A", "snippet": "content"}],
            topic="AI",
        )
        assert result == []


# ---------------------------------------------------------------------------
# MultiRoundSearcher
# ---------------------------------------------------------------------------

class TestMultiRoundSearcher:

    def _make_searcher(self, search_results=None, gaps=None):
        mock_search = MagicMock()
        mock_search.search.return_value = {
            "success": True,
            "results": search_results or [{"url": "https://a.com", "title": "A", "snippet": "..."}],
        }
        mock_detector = MagicMock()
        mock_detector.detect.return_value = gaps or []
        mock_detector.should_continue.side_effect = lambda g, r, m: len(g) > 0 and r < m
        return MultiRoundSearcher(
            search_service=mock_search,
            gap_detector=mock_detector,
        )

    def test_single_round_no_gaps(self):
        """无空白 → 只搜索 1 轮"""
        searcher = self._make_searcher(gaps=[])
        result = searcher.search("AI", article_type="medium")
        assert result["rounds"] == 1
        assert len(result["results"]) > 0

    def test_multi_round_with_gaps(self):
        """有空白 → 多轮搜索"""
        mock_search = MagicMock()
        mock_search.search.return_value = {
            "success": True,
            "results": [{"url": "https://a.com", "title": "A", "snippet": "..."}],
        }
        mock_detector = MagicMock()
        # 第 1 轮有空白，第 2 轮无空白
        mock_detector.detect.side_effect = [
            [{"gap": "缺少X", "refined_query": "X 详解"}],
            [],
        ]
        mock_detector.should_continue.side_effect = lambda g, r, m: len(g) > 0 and r < m

        searcher = MultiRoundSearcher(
            search_service=mock_search,
            gap_detector=mock_detector,
        )
        result = searcher.search("AI", article_type="medium")
        assert result["rounds"] == 2
        assert len(result["gaps_found"]) == 1

    def test_max_rounds_respected(self):
        """达到最大轮数 → 停止"""
        mock_search = MagicMock()
        mock_search.search.return_value = {
            "success": True,
            "results": [{"url": f"https://r{i}.com", "title": f"R{i}", "snippet": "..."} for i in range(3)],
        }
        mock_detector = MagicMock()
        # 每轮都有空白
        mock_detector.detect.return_value = [{"gap": "always gap", "refined_query": "q"}]
        mock_detector.should_continue.side_effect = lambda g, r, m: len(g) > 0 and r < m

        searcher = MultiRoundSearcher(
            search_service=mock_search,
            gap_detector=mock_detector,
        )
        result = searcher.search("AI", article_type="short")  # max 3 rounds
        assert result["rounds"] == 3

    def test_url_dedup(self):
        """URL 去重"""
        mock_search = MagicMock()
        mock_search.search.return_value = {
            "success": True,
            "results": [{"url": "https://same.com", "title": "Same", "snippet": "..."}],
        }
        mock_detector = MagicMock()
        mock_detector.detect.side_effect = [
            [{"gap": "gap1", "refined_query": "q1"}],
            [],
        ]
        mock_detector.should_continue.side_effect = lambda g, r, m: len(g) > 0 and r < m

        searcher = MultiRoundSearcher(
            search_service=mock_search,
            gap_detector=mock_detector,
        )
        result = searcher.search("AI", article_type="medium")
        urls = [r["url"] for r in result["results"]]
        assert len(urls) == len(set(urls))

    def test_search_failure_stops(self):
        """搜索失败 → 停止"""
        mock_search = MagicMock()
        mock_search.search.return_value = {"success": False, "results": []}
        mock_detector = MagicMock()

        searcher = MultiRoundSearcher(
            search_service=mock_search,
            gap_detector=mock_detector,
        )
        result = searcher.search("AI", article_type="medium")
        assert result["rounds"] == 1
        assert len(result["results"]) == 0
