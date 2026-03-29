"""
三层上下文管理中间件单元测试

测试 ContextManagementMiddleware 的三层压缩策略：
  Layer 1 (fold_threshold ~ summary_threshold): 语义压缩
  Layer 2 (summary_threshold ~ 1.0): LLM 主动压缩 (AgentFold)
  Layer 3 (>= summary_threshold 且 research_data 不足): 全量摘要 (ReSum)
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# 将 backend 加入 sys.path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.blog_generator.context_management_middleware import (
    ContextManagementMiddleware,
    RESUM_INITIAL_PROMPT,
    RESUM_INCREMENTAL_PROMPT,
)


# ---- Fixtures ----

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat.return_value = "compressed research summary"
    return llm


@pytest.fixture
def mock_semantic_compressor():
    sc = MagicMock()
    sc.compress.return_value = [{"title": "relevant", "content": "data"}]
    return sc


@pytest.fixture
def middleware(mock_llm, mock_semantic_compressor):
    return ContextManagementMiddleware(
        llm_service=mock_llm,
        semantic_compressor=mock_semantic_compressor,
        model_name="gpt-4o",
    )


@pytest.fixture
def small_state():
    """usage < fold_threshold"""
    return {"topic": "test", "research_data": "short text"}


# ---- TestFeatureToggle ----

class TestFeatureToggle:
    """CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED defaults to false"""

    def test_disabled_by_default(self, middleware):
        """Default env is 'false', middleware should be a no-op."""
        with patch.object(middleware, "_estimate_usage", return_value=0.95):
            state = {"topic": "t", "research_data": "x" * 10000}
            result = middleware.before_node(state, "writer")
            assert result is None

    def test_enabled_via_env(self, middleware):
        """When explicitly enabled and usage high, should return a patch."""
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.95):
                state = {
                    "topic": "test",
                    "research_data": "x" * 10000,
                    "distilled_sources": [{"src": "d"}],
                }
                result = middleware.before_node(state, "writer")
                assert result is not None

    def test_explicitly_disabled(self, middleware):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "false"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.95):
                state = {"topic": "t", "research_data": "x" * 100000}
                result = middleware.before_node(state, "writer")
                assert result is None


class TestNoCompression:
    """Below fold_threshold (0.7), no compression should trigger."""

    def test_no_compression_below_threshold(self, middleware, small_state):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            result = middleware.before_node(small_state, "writer")
            assert result is None  # usage too low


# ---- TestLayer1 ----

class TestLayer1:
    """Layer 1: SemanticCompressor (fold_threshold <= usage < summary_threshold)"""

    def test_layer1_triggers_semantic_compression(self, middleware, mock_semantic_compressor):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.75):
                state = {"topic": "test", "search_results": [{"content": "data"}] * 20}
                result = middleware.before_node(state, "writer")
                assert result is not None
                assert result.get("_context_layer") == 1
                mock_semantic_compressor.compress.assert_called_once()

    def test_layer1_skips_without_search_results(self, middleware):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.75):
                state = {"topic": "test", "search_results": []}
                result = middleware.before_node(state, "writer")
                # No search results -> Layer 1 has nothing to compress
                assert result is None or result.get("_context_layer") is None

    def test_layer1_without_semantic_compressor(self):
        """If no semantic_compressor injected, Layer 1 returns empty."""
        mw = ContextManagementMiddleware(llm_service=MagicMock(), model_name="gpt-4o")
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(mw, "_estimate_usage", return_value=0.75):
                state = {"topic": "test", "search_results": [{"content": "x"}] * 20}
                result = mw.before_node(state, "writer")
                assert result is None or result.get("_context_layer") is None


# ---- TestLayer2 ----

class TestLayer2:
    """Layer 2: LLM active compression (AgentFold style)"""

    def test_layer2_triggers_llm_compression(self, middleware, mock_llm):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.92):
                state = {"topic": "test", "research_data": "x" * 5000}
                result = middleware.before_node(state, "writer")
                assert result is not None
                assert result.get("_context_layer") == 2
                assert "research_data" in result

    def test_layer2_degrades_to_layer1_on_failure(self, middleware, mock_llm):
        mock_llm.chat.side_effect = Exception("LLM error")
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.92):
                state = {
                    "topic": "test",
                    "research_data": "x" * 5000,
                    "search_results": [{"content": "y"}] * 20,
                }
                # Should not raise; degrades gracefully
                result = middleware.before_node(state, "writer")
                # Either Layer 1 result or None, but no exception
                assert result is None or result.get("_context_layer") in (1, None)

    def test_layer2_skips_short_research_data(self, middleware):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.92):
                state = {"topic": "test", "research_data": "short"}
                result = middleware.before_node(state, "writer")
                # research_data too short -> degrades to Layer 1
                assert result is None or result.get("_context_layer") != 2


class TestLayer3:
    """Layer 3: ReSum full summary (>= summary_threshold with context_parts)"""

    def test_layer3_triggers_full_summary(self, middleware, mock_llm):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.95):
                state = {
                    "topic": "test",
                    "research_data": "x" * 10000,
                    "distilled_sources": [{"src": "data"}],
                }
                result = middleware.before_node(state, "writer")
                assert result is not None
                assert result.get("_context_layer") == 3
                assert "_context_summary" in result

    def test_layer3_clears_distilled_sources(self, middleware, mock_llm):
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.95):
                state = {
                    "topic": "test",
                    "research_data": "x" * 10000,
                    "distilled_sources": [{"src": "data"}] * 10,
                }
                result = middleware.before_node(state, "writer")
                assert result.get("distilled_sources") == []

    def test_layer3_uses_incremental_prompt_on_second_call(self, middleware, mock_llm):
        middleware._last_summary = "previous summary"
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.95):
                state = {
                    "topic": "test",
                    "research_data": "x" * 10000,
                    "distilled_sources": [{"src": "d"}],
                }
                middleware.before_node(state, "writer")
                # Verify incremental prompt was used (contains last_summary reference)
                call_kwargs = mock_llm.chat.call_args[1]
                prompt_content = call_kwargs["messages"][0]["content"]
                assert "previous summary" in prompt_content or "上次摘要" in prompt_content

    def test_layer3_degrades_on_failure(self, middleware, mock_llm):
        """Layer 3 failure should degrade to Layer 2."""
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("summary failed")
            return "compressed fallback"

        mock_llm.chat.side_effect = side_effect
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.95):
                state = {
                    "topic": "test",
                    "research_data": "x" * 5000,
                    "distilled_sources": [{"src": "d"}],
                }
                result = middleware.before_node(state, "writer")
                # Should degrade gracefully, not raise
                assert result is None or isinstance(result, dict)


# ---- TestAfterNode ----

class TestAfterNode:
    """after_node should be a no-op."""

    def test_after_node_returns_none(self, middleware):
        result = middleware.after_node({"topic": "test"}, "writer")
        assert result is None


# ---- TestEstimateUsage ----

class TestEstimateUsage:
    """_estimate_usage should compute ratio from state fields."""

    def test_empty_state_returns_zero(self, middleware):
        assert middleware._estimate_usage({}) == 0.0

    def test_large_state_returns_high_ratio(self, middleware):
        state = {"research_data": "x" * 500000}
        ratio = middleware._estimate_usage(state)
        assert ratio > 0.0


# ---- TestMiddlewarePipelineIntegration ----

class TestMiddlewarePipelineIntegration:
    """Integration: ContextManagementMiddleware works with MiddlewarePipeline."""

    def test_middleware_registered_in_pipeline(self):
        from services.blog_generator.middleware import MiddlewarePipeline
        mw = ContextManagementMiddleware()
        pipeline = MiddlewarePipeline(middlewares=[mw])
        assert len(pipeline.middlewares) == 1

    def test_wrap_node_invokes_before_node(self, middleware):
        from services.blog_generator.middleware import MiddlewarePipeline
        pipeline = MiddlewarePipeline(middlewares=[middleware])

        def dummy_node(state):
            return state

        wrapped = pipeline.wrap_node("writer", dummy_node)
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED": "true"}):
            with patch.object(middleware, "_estimate_usage", return_value=0.75):
                result = wrapped({"topic": "test", "search_results": [{"content": "x"}] * 20})
                assert isinstance(result, dict)
