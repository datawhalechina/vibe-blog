"""
75.04 知识空白检测与多轮搜索 — 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.services.knowledge_gap_detector import (
    KnowledgeGapDetector,
    MAX_SEARCH_ROUNDS,
)


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
