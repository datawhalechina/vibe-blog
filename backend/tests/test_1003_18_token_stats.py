"""
Token 统计增强 — 多维聚合 单元测试
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.token_stats import TokenUsageRecord, TokenStats


class TestTokenStats:

    def test_record_and_total(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=100, output_tokens=50, cached_tokens=10)
        stats.record("reviewer", "claude-3.5-sonnet", input_tokens=200, output_tokens=80, cached_tokens=20)

        total = stats.total()
        assert total["calls"] == 2
        assert total["input"] == 300
        assert total["output"] == 130
        assert total["cached"] == 30

    def test_by_agent(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=100, output_tokens=50, cached_tokens=10)
        stats.record("reviewer", "claude-3.5-sonnet", input_tokens=200, output_tokens=80)
        stats.record("writer", "gpt-4o", input_tokens=50, output_tokens=30, cached_tokens=5)

        by_agent = stats.by_agent()
        assert "writer" in by_agent
        assert "reviewer" in by_agent
        assert by_agent["writer"]["calls"] == 2
        assert by_agent["writer"]["input"] == 150
        assert by_agent["writer"]["output"] == 80
        assert by_agent["writer"]["cached"] == 15
        assert by_agent["reviewer"]["calls"] == 1
        assert by_agent["reviewer"]["input"] == 200

    def test_by_model(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=100, output_tokens=50)
        stats.record("reviewer", "gpt-4o", input_tokens=200, output_tokens=80)
        stats.record("writer", "claude-3.5-sonnet", input_tokens=50, output_tokens=30)

        by_model = stats.by_model()
        assert "gpt-4o" in by_model
        assert "claude-3.5-sonnet" in by_model
        assert by_model["gpt-4o"]["calls"] == 2
        assert by_model["gpt-4o"]["input"] == 300
        assert by_model["gpt-4o"]["output"] == 130
        assert by_model["claude-3.5-sonnet"]["calls"] == 1
        assert by_model["claude-3.5-sonnet"]["input"] == 50

    def test_top_consumers_agent(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=1000, output_tokens=500)
        stats.record("reviewer", "gpt-4o", input_tokens=200, output_tokens=100)
        stats.record("searcher", "gpt-4o", input_tokens=500, output_tokens=250)

        top = stats.top_consumers(n=2, dimension="agent")
        assert len(top) == 2
        assert top[0]["name"] == "writer"
        assert top[0]["total"] == 1500
        assert top[1]["name"] == "searcher"
        assert top[1]["total"] == 750

    def test_top_consumers_model(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=1000, output_tokens=500)
        stats.record("writer", "claude-3.5-sonnet", input_tokens=200, output_tokens=100)

        top = stats.top_consumers(n=5, dimension="model")
        assert len(top) == 2
        assert top[0]["name"] == "gpt-4o"
        assert top[0]["total"] == 1500

    def test_cached_tokens(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=100, output_tokens=50, cached_tokens=40)

        total = stats.total()
        assert total["cached"] == 40

        by_agent = stats.by_agent()
        assert by_agent["writer"]["cached"] == 40

        by_model = stats.by_model()
        assert by_model["gpt-4o"]["cached"] == 40

    def test_clear(self):
        stats = TokenStats()
        stats.record("writer", "gpt-4o", input_tokens=100, output_tokens=50)
        stats.clear()

        total = stats.total()
        assert total["calls"] == 0
        assert total["input"] == 0
        assert total["output"] == 0
        assert total["cached"] == 0

    def test_empty_total(self):
        stats = TokenStats()
        total = stats.total()
        assert total["calls"] == 0
        assert total["input"] == 0
        assert total["output"] == 0
        assert total["cached"] == 0
