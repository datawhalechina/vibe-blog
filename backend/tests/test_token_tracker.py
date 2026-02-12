"""
37.31 统一 Token 追踪与成本分析 — 单元测试
"""
import pytest
from utils.token_tracker import (
    TokenUsage, TokenTracker,
    extract_token_usage_from_langchain,
    estimate_cost, PRICING, _match_pricing,
)


# ============ TokenUsage 测试 ============

class TestTokenUsage:
    def test_defaults(self):
        u = TokenUsage()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.cache_read_tokens == 0
        assert u.cache_write_tokens == 0
        assert u.model == ""
        assert u.provider == ""

    def test_total_tokens(self):
        u = TokenUsage(input_tokens=100, output_tokens=50)
        assert u.total_tokens == 150

    def test_with_model_info(self):
        u = TokenUsage(input_tokens=10, model="gpt-4o", provider="openai")
        assert u.model == "gpt-4o"
        assert u.provider == "openai"


# ============ TokenTracker 测试 ============

class TestTokenTracker:
    def test_record_single(self):
        tracker = TokenTracker()
        usage = TokenUsage(input_tokens=100, output_tokens=50,
                           cache_read_tokens=10, cache_write_tokens=5)
        tracker.record(usage, agent="writer")

        assert tracker.total_input_tokens == 100
        assert tracker.total_output_tokens == 50
        assert tracker.total_cache_read_tokens == 10
        assert tracker.total_cache_write_tokens == 5
        assert tracker.last_call is usage
        assert len(tracker.call_history) == 1

    def test_record_multiple_cumulative(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(input_tokens=100, output_tokens=50), agent="writer")
        tracker.record(TokenUsage(input_tokens=200, output_tokens=80), agent="reviewer")
        tracker.record(TokenUsage(input_tokens=50, output_tokens=30), agent="writer")

        assert tracker.total_input_tokens == 350
        assert tracker.total_output_tokens == 160
        assert len(tracker.call_history) == 3

    def test_agent_grouping(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(input_tokens=100, output_tokens=50,
                                  cache_read_tokens=10), agent="writer")
        tracker.record(TokenUsage(input_tokens=200, output_tokens=80), agent="reviewer")
        tracker.record(TokenUsage(input_tokens=50, output_tokens=30,
                                  cache_read_tokens=5), agent="writer")

        assert "writer" in tracker.agent_usage
        assert "reviewer" in tracker.agent_usage
        assert tracker.agent_usage["writer"]["input"] == 150
        assert tracker.agent_usage["writer"]["output"] == 80
        assert tracker.agent_usage["writer"]["cache_read"] == 15
        assert tracker.agent_usage["writer"]["calls"] == 2
        assert tracker.agent_usage["reviewer"]["calls"] == 1

    def test_default_agent_unknown(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(input_tokens=10, output_tokens=5))
        assert "unknown" in tracker.agent_usage

    def test_get_summary(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(input_tokens=100, output_tokens=50,
                                  cache_read_tokens=10, cache_write_tokens=5,
                                  model="gpt-4o"), agent="writer")
        tracker.record(TokenUsage(input_tokens=200, output_tokens=80), agent="reviewer")

        summary = tracker.get_summary()
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 130
        assert summary["total_cache_read_tokens"] == 10
        assert summary["total_cache_write_tokens"] == 5
        assert summary["total_tokens"] == 430
        assert summary["total_calls"] == 2
        assert "writer" in summary["agent_breakdown"]
        assert "reviewer" in summary["agent_breakdown"]

    def test_format_summary(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(input_tokens=1000, output_tokens=500), agent="writer")
        tracker.record(TokenUsage(input_tokens=2000, output_tokens=800), agent="reviewer")

        text = tracker.format_summary()
        assert "Token Usage" in text
        assert "3,000" in text  # cumulative input tokens formatted
        assert "writer" in text
        assert "reviewer" in text

    def test_format_summary_empty(self):
        tracker = TokenTracker()
        text = tracker.format_summary()
        assert "Token Usage" in text
        assert "0" in text


# ============ extract_token_usage_from_langchain 测试 ============

class TestExtractTokenUsage:
    def test_langchain_aimessage_basic(self):
        """LangChain AIMessage 基本格式"""
        class MockResponse:
            usage_metadata = {
                "input_tokens": 1500,
                "output_tokens": 800,
                "total_tokens": 2300,
            }
        usage = extract_token_usage_from_langchain(MockResponse(), model="gpt-4o", provider="openai")
        assert usage.input_tokens == 1500
        assert usage.output_tokens == 800
        assert usage.model == "gpt-4o"

    def test_langchain_aimessage_with_openai_cache(self):
        """LangChain AIMessage + OpenAI 缓存字段"""
        class MockResponse:
            usage_metadata = {
                "input_tokens": 1500,
                "output_tokens": 800,
                "input_token_details": {"cached": 500},
            }
        usage = extract_token_usage_from_langchain(MockResponse())
        assert usage.input_tokens == 1500
        assert usage.cache_read_tokens == 500
        assert usage.cache_write_tokens == 0

    def test_langchain_aimessage_with_anthropic_cache(self):
        """LangChain AIMessage + Anthropic 缓存字段"""
        class MockResponse:
            usage_metadata = {
                "input_tokens": 1500,
                "output_tokens": 800,
                "input_token_details": {
                    "cache_read": 300,
                    "cache_creation": 200,
                },
            }
        usage = extract_token_usage_from_langchain(MockResponse())
        assert usage.cache_read_tokens == 300
        assert usage.cache_write_tokens == 200

    def test_raw_openai_response(self):
        """原始 OpenAI 响应格式"""
        class MockDetails:
            cached_tokens = 100
        class MockUsage:
            prompt_tokens = 1000
            completion_tokens = 500
            prompt_tokens_details = MockDetails()
        class MockResponse:
            usage_metadata = None
            usage = MockUsage()
        usage = extract_token_usage_from_langchain(MockResponse(), model="gpt-4o")
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cache_read_tokens == 100

    def test_raw_openai_no_details(self):
        """原始 OpenAI 响应，无 details"""
        class MockUsage:
            prompt_tokens = 1000
            completion_tokens = 500
            prompt_tokens_details = None
        class MockResponse:
            usage_metadata = None
            usage = MockUsage()
        usage = extract_token_usage_from_langchain(MockResponse())
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cache_read_tokens == 0

    def test_no_usage_data(self):
        """无 token 数据的响应"""
        class MockResponse:
            pass
        usage = extract_token_usage_from_langchain(MockResponse())
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_none_usage_metadata(self):
        """usage_metadata 为 None"""
        class MockResponse:
            usage_metadata = None
        usage = extract_token_usage_from_langchain(MockResponse())
        assert usage.input_tokens == 0

    def test_exception_handling(self):
        """提取异常不中断流程"""
        class MockResponse:
            @property
            def usage_metadata(self):
                raise RuntimeError("bad data")
        usage = extract_token_usage_from_langchain(MockResponse())
        assert usage.input_tokens == 0


# ============ 成本估算测试 ============

class TestEstimateCost:
    def test_basic_cost(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(
            input_tokens=1_000_000, output_tokens=500_000,
            model="gpt-4o", provider="openai"
        ))
        cost = estimate_cost(tracker)
        # 1M * 2.50 + 0.5M * 10.00 = 2.50 + 5.00 = 7.50
        assert abs(cost - 7.50) < 0.01

    def test_cost_with_cache(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(
            input_tokens=1_000_000, output_tokens=500_000,
            cache_read_tokens=200_000,
            model="gpt-4o", provider="openai"
        ))
        cost = estimate_cost(tracker)
        # 1M * 2.50 + 0.5M * 10.00 + 0.2M * 1.25 = 2.50 + 5.00 + 0.25 = 7.75
        assert abs(cost - 7.75) < 0.01

    def test_unknown_model_zero_cost(self):
        tracker = TokenTracker()
        tracker.record(TokenUsage(
            input_tokens=1000, output_tokens=500,
            model="unknown-model"
        ))
        cost = estimate_cost(tracker)
        assert cost == 0.0

    def test_empty_tracker(self):
        tracker = TokenTracker()
        assert estimate_cost(tracker) == 0.0


class TestMatchPricing:
    def test_exact_match(self):
        assert _match_pricing("gpt-4o") == PRICING["gpt-4o"]

    def test_prefix_match(self):
        prices = _match_pricing("gpt-4o-2024-08-06")
        assert prices == PRICING["gpt-4o"]

    def test_no_match(self):
        assert _match_pricing("unknown-model") == {}

    def test_empty_string(self):
        assert _match_pricing("") == {}
