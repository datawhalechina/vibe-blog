"""
113.02 GoalDirectedExtractor -- Unit Tests

Tests for goal-directed web extraction:
- ExtractionResult dataclass
- truncate_to_tokens (tiktoken precision)
- _parse_extraction_json (fault-tolerant JSON parsing)
- extract() main flow
- Progressive retry degradation
- DeepScraper integration (feature toggle)
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.services.goal_directed_extractor import (
    GoalDirectedExtractor,
    ExtractionResult,
    GOAL_EXTRACTOR_PROMPT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """Mock LLM service that returns valid extraction JSON."""
    service = MagicMock()
    service.chat.return_value = json.dumps({
        "rational": "Article paragraph 3 discusses RAG retrieval mechanism",
        "evidence": "RAG combines external knowledge bases with LLMs...",
        "summary": "RAG is a technical architecture combining retrieval and generation",
    })
    return service


@pytest.fixture
def sample_content():
    """Sample webpage content."""
    return "# RAG Technical Deep Dive\n\n" + "This is a detailed article about RAG. " * 500


@pytest.fixture
def extractor(mock_llm):
    """GoalDirectedExtractor with mock LLM."""
    return GoalDirectedExtractor(llm_service=mock_llm)

# ---------------------------------------------------------------------------
# ExtractionResult
# ---------------------------------------------------------------------------

class TestExtractionResult:

    def test_default_values(self):
        r = ExtractionResult()
        assert r.rational == ""
        assert r.evidence == ""
        assert r.summary == ""
        assert r.success is True
        assert r.error == ""

    def test_failure_result(self):
        r = ExtractionResult(success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"


# ---------------------------------------------------------------------------
# truncate_to_tokens
# ---------------------------------------------------------------------------

class TestTruncateToTokens:

    def test_short_text_unchanged(self):
        text = "Hello world"
        result = GoalDirectedExtractor.truncate_to_tokens(text, 100)
        assert result == text

    def test_long_text_truncated_precisely(self):
        text = "Hello " * 100000
        result = GoalDirectedExtractor.truncate_to_tokens(text, 1000)
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            assert len(enc.encode(result)) <= 1000
        except ImportError:
            # fallback: char-based check
            assert len(result) <= 1000 * 4

    def test_empty_text(self):
        result = GoalDirectedExtractor.truncate_to_tokens("", 100)
        assert result == ""


# ---------------------------------------------------------------------------
# _parse_extraction_json
# ---------------------------------------------------------------------------

class TestParseExtractionJson:

    def test_valid_json(self):
        raw = '{"rational": "a", "evidence": "b", "summary": "c"}'
        result = GoalDirectedExtractor._parse_extraction_json(raw)
        assert result["rational"] == "a"
        assert result["evidence"] == "b"
        assert result["summary"] == "c"

    def test_json_with_markdown_code_block(self):
        raw = '```json\n{"rational": "a", "evidence": "b", "summary": "c"}\n```'
        result = GoalDirectedExtractor._parse_extraction_json(raw)
        assert result is not None
        assert result["summary"] == "c"

    def test_json_with_generic_code_block(self):
        raw = '```\n{"rational": "x", "evidence": "y", "summary": "z"}\n```'
        result = GoalDirectedExtractor._parse_extraction_json(raw)
        assert result is not None
        assert result["rational"] == "x"

    def test_json_with_surrounding_text(self):
        raw = 'Here is the result: {"rational": "a", "evidence": "b", "summary": "c"} done.'
        result = GoalDirectedExtractor._parse_extraction_json(raw)
        assert result is not None
        assert result["evidence"] == "b"

    def test_invalid_json_returns_none(self):
        result = GoalDirectedExtractor._parse_extraction_json("not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = GoalDirectedExtractor._parse_extraction_json("")
        assert result is None

    def test_none_returns_none(self):
        result = GoalDirectedExtractor._parse_extraction_json(None)
        assert result is None

    def test_whitespace_only_returns_none(self):
        result = GoalDirectedExtractor._parse_extraction_json("   \n  ")
        assert result is None


# ---------------------------------------------------------------------------
# extract() main flow
# ---------------------------------------------------------------------------

class TestExtract:

    def test_returns_structured_result(self, extractor, sample_content):
        result = extractor.extract(sample_content, "RAG retrieval augmented generation")
        assert result.success is True
        assert result.rational != ""
        assert result.evidence != ""
        assert result.summary != ""

    def test_empty_content_returns_failure(self, extractor):
        result = extractor.extract("", "any goal")
        assert result.success is False
        assert "空内容" in result.error

    def test_whitespace_content_returns_failure(self, extractor):
        result = extractor.extract("   \n  ", "any goal")
        assert result.success is False

    def test_no_llm_returns_truncated_original(self, sample_content):
        ext = GoalDirectedExtractor(llm_service=None)
        result = ext.extract(sample_content, "RAG")
        assert result.success is True
        assert len(result.evidence) <= 2000
        assert result.rational == "无 LLM 服务，返回截断原文"

    def test_llm_called_with_goal_in_prompt(self, mock_llm, sample_content):
        ext = GoalDirectedExtractor(llm_service=mock_llm)
        ext.extract(sample_content, "RAG retrieval mechanism")
        call_args = mock_llm.chat.call_args
        messages = call_args[0][0]  # positional arg
        assert "RAG retrieval mechanism" in messages[0]["content"]

    def test_custom_model_passed_to_llm(self, mock_llm, sample_content):
        with patch.dict(os.environ, {"GOAL_EXTRACTOR_MODEL": "gpt-4o-mini"}):
            ext = GoalDirectedExtractor(llm_service=mock_llm)
            ext.extract(sample_content, "test goal")
            call_kwargs = mock_llm.chat.call_args[1]
            assert call_kwargs.get("model") == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Progressive retry
# ---------------------------------------------------------------------------

class TestProgressiveRetry:

    def test_retry_on_empty_response(self, mock_llm, sample_content):
        mock_llm.chat.side_effect = [
            "",
            "",
            json.dumps({"rational": "r", "evidence": "e", "summary": "s"}),
        ]
        ext = GoalDirectedExtractor(llm_service=mock_llm)
        result = ext.extract(sample_content, "test goal")
        assert result.summary == "s"
        assert mock_llm.chat.call_count >= 3

    def test_all_retries_fail_returns_failure(self, mock_llm, sample_content):
        mock_llm.chat.side_effect = Exception("LLM error")
        ext = GoalDirectedExtractor(llm_service=mock_llm)
        result = ext.extract(sample_content, "test goal")
        assert result.success is False

    def test_retry_on_invalid_json(self, mock_llm, sample_content):
        mock_llm.chat.side_effect = [
            "not json",
            "still not json",
            "nope",
            json.dumps({"rational": "r", "evidence": "e", "summary": "s"}),
        ]
        ext = GoalDirectedExtractor(llm_service=mock_llm)
        result = ext.extract(sample_content, "test goal")
        # 4 retries (retry_ratios has 4 entries), last one succeeds
        assert result.summary == "s"


# ---------------------------------------------------------------------------
# DeepScraper integration
# ---------------------------------------------------------------------------

class TestDeepScraperIntegration:

    def test_scrape_top_n_with_goal_extraction_enabled(self, mock_llm):
        """When GOAL_EXTRACTION_ENABLED=true, results contain structured fields."""
        from services.blog_generator.services.deep_scraper import DeepScraper
        with patch.dict(os.environ, {"GOAL_EXTRACTION_ENABLED": "true"}):
            scraper = DeepScraper(llm_service=mock_llm)
            scraper._scrape_single = MagicMock(return_value="Web page content...")
            results = [{"url": "https://example.com", "title": "Test"}]
            enriched = scraper.scrape_top_n(results, "RAG", goal="RAG retrieval")
            assert len(enriched) == 1
            assert "evidence" in enriched[0]
            assert "rational" in enriched[0]
            assert "summary" in enriched[0]
            assert enriched[0]["extraction_success"] is True

    def test_scrape_top_n_fallback_when_disabled(self, mock_llm):
        """When GOAL_EXTRACTION_ENABLED=false, falls back to original _extract_info."""
        from services.blog_generator.services.deep_scraper import DeepScraper
        with patch.dict(os.environ, {"GOAL_EXTRACTION_ENABLED": "false"}):
            scraper = DeepScraper(llm_service=mock_llm)
            scraper._scrape_single = MagicMock(return_value="Web page content...")
            results = [{"url": "https://example.com", "title": "Test"}]
            enriched = scraper.scrape_top_n(results, "RAG")
            assert len(enriched) == 1
            assert "extracted_info" in enriched[0]
            # Should NOT have goal-extraction fields
            assert "rational" not in enriched[0]

    def test_scrape_top_n_default_disabled(self, mock_llm):
        """Default: GOAL_EXTRACTION_ENABLED not set -> disabled (false)."""
        from services.blog_generator.services.deep_scraper import DeepScraper
        env = {k: v for k, v in os.environ.items() if k != "GOAL_EXTRACTION_ENABLED"}
        with patch.dict(os.environ, env, clear=True):
            scraper = DeepScraper(llm_service=mock_llm)
            scraper._scrape_single = MagicMock(return_value="Content")
            results = [{"url": "https://example.com", "title": "T"}]
            enriched = scraper.scrape_top_n(results, "topic")
            assert len(enriched) == 1
            assert "extracted_info" in enriched[0]

    def test_scrape_top_n_goal_parameter_forwarded(self, mock_llm):
        """The goal parameter is forwarded to the extractor."""
        from services.blog_generator.services.deep_scraper import DeepScraper
        with patch.dict(os.environ, {"GOAL_EXTRACTION_ENABLED": "true"}):
            scraper = DeepScraper(llm_service=mock_llm)
            scraper._scrape_single = MagicMock(return_value="Content")
            results = [{"url": "https://example.com", "title": "T"}]
            enriched = scraper.scrape_top_n(results, "AI", goal="specific RAG goal")
            # Verify LLM was called with the specific goal
            call_args = mock_llm.chat.call_args
            prompt_content = call_args[0][0][0]["content"]
            assert "specific RAG goal" in prompt_content

