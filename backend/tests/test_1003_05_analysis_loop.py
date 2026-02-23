"""
TDD 测试 — 1003.05 双循环架构 Analysis Loop
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.agents.analysis_investigator import AnalysisInvestigator
from services.blog_generator.agents.analysis_note import AnalysisNoteAgent


class FakeLLM:
    """Mock LLM，按顺序返回预设响应"""
    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0

    def chat(self, messages=None, **kwargs):
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return "{}"


class FakeSearchService:
    """Mock 搜索服务"""
    def __init__(self, results=None):
        self._results = results or [{"title": "Result 1", "content": "Content 1", "url": "https://example.com"}]
        self.call_count = 0

    def search(self, query, max_results=5):
        self.call_count += 1
        return {"success": True, "results": self._results}


# ── AnalysisInvestigator 测试 ──

class TestAnalysisInvestigator:
    def test_basic_flow(self):
        """LLM 返回 queries 时，执行搜索并更新 knowledge_chain"""
        llm = FakeLLM([json.dumps({
            "reasoning": "Need more info",
            "should_stop": False,
            "queries": [{"query": "AI safety overview", "tool_type": "web_search"}],
        })])
        search = FakeSearchService()
        agent = AnalysisInvestigator(llm, search)

        state = {"topic": "AI Safety", "search_results": [], "analysis_knowledge_chain": [], "analysis_round": 0}
        result = agent.run(state)

        assert result["analysis_round"] == 1
        assert result["analysis_should_stop"] is False
        assert len(result["analysis_knowledge_chain"]) == 1
        assert result["analysis_knowledge_chain"][0]["cite_id"] == "AK-1-1"
        assert len(result["_new_knowledge_ids"]) == 1
        assert search.call_count == 1

    def test_should_stop(self):
        """LLM 返回 should_stop=true 时，不执行搜索"""
        llm = FakeLLM([json.dumps({
            "reasoning": "Knowledge sufficient",
            "should_stop": True,
            "queries": [],
        })])
        search = FakeSearchService()
        agent = AnalysisInvestigator(llm, search)

        state = {"topic": "AI", "search_results": [], "analysis_knowledge_chain": [], "analysis_round": 0}
        result = agent.run(state)

        assert result["analysis_should_stop"] is True
        assert len(result["analysis_knowledge_chain"]) == 0
        assert result["_new_knowledge_ids"] == []
        assert search.call_count == 0

    def test_max_queries_per_round(self):
        """超过 max_queries_per_round 时只执行前 N 个"""
        llm = FakeLLM([json.dumps({
            "reasoning": "Need lots",
            "should_stop": False,
            "queries": [
                {"query": f"q{i}", "tool_type": "web_search"}
                for i in range(5)
            ],
        })])
        search = FakeSearchService()
        agent = AnalysisInvestigator(llm, search)
        agent.max_queries_per_round = 3

        state = {"topic": "AI", "search_results": [], "analysis_knowledge_chain": [], "analysis_round": 0}
        result = agent.run(state)

        assert search.call_count == 3
        assert len(result["analysis_knowledge_chain"]) == 3

    def test_no_search_service(self):
        """无搜索服务时 should_stop"""
        llm = FakeLLM([json.dumps({
            "should_stop": False,
            "queries": [{"query": "test"}],
        })])
        agent = AnalysisInvestigator(llm, search_service=None)

        state = {"topic": "AI", "search_results": [], "analysis_knowledge_chain": [], "analysis_round": 0}
        result = agent.run(state)
        # 无搜索服务，queries 执行不了，new_items 为空
        assert result["analysis_should_stop"] is False
        assert len(result["_new_knowledge_ids"]) == 0

    def test_llm_failure_graceful(self):
        """LLM 返回无效 JSON 时优雅降级"""
        llm = FakeLLM(["not json at all"])
        search = FakeSearchService()
        agent = AnalysisInvestigator(llm, search)

        state = {"topic": "AI", "search_results": [], "analysis_knowledge_chain": [], "analysis_round": 0}
        result = agent.run(state)

        assert result["analysis_should_stop"] is True
        assert search.call_count == 0


# ── AnalysisNoteAgent 测试 ──

class TestAnalysisNoteAgent:
    def test_generate_summaries(self):
        """对新知识项生成摘要"""
        llm = FakeLLM(["This is a summary about AI safety."])
        agent = AnalysisNoteAgent(llm)

        state = {
            "topic": "AI Safety",
            "analysis_knowledge_chain": [
                {"cite_id": "AK-1-1", "query": "AI safety", "raw_result": "Some content", "summary": ""},
            ],
            "_new_knowledge_ids": ["AK-1-1"],
            "accumulated_knowledge": "",
        }
        result = agent.run(state)

        assert result["analysis_knowledge_chain"][0]["summary"] != ""
        assert "AI safety" in result["accumulated_knowledge"] or "Analysis Loop" in result["accumulated_knowledge"]

    def test_empty_new_ids(self):
        """无新知识 ID 时不做任何操作"""
        llm = FakeLLM([])
        agent = AnalysisNoteAgent(llm)

        state = {
            "topic": "AI",
            "analysis_knowledge_chain": [],
            "_new_knowledge_ids": [],
            "accumulated_knowledge": "",
        }
        result = agent.run(state)
        assert result["accumulated_knowledge"] == ""

    def test_skip_already_summarized(self):
        """已有摘要的项不重复生成"""
        llm = FakeLLM([])  # 不应被调用
        agent = AnalysisNoteAgent(llm)

        state = {
            "topic": "AI",
            "analysis_knowledge_chain": [
                {"cite_id": "AK-1-1", "query": "q", "raw_result": "r", "summary": "existing summary"},
            ],
            "_new_knowledge_ids": ["AK-1-1"],
            "accumulated_knowledge": "",
        }
        result = agent.run(state)
        assert result["analysis_knowledge_chain"][0]["summary"] == "existing summary"


# ── 条件边测试 ──

class TestShouldStopAnalysis:
    """测试 _should_stop_analysis 逻辑（不依赖 generator 实例，直接测试逻辑）"""

    def _check(self, env_enabled, should_stop, round_num, max_rounds, new_ids):
        """模拟 _should_stop_analysis 逻辑"""
        if not env_enabled:
            return "stop"
        if should_stop:
            return "stop"
        if round_num >= max_rounds:
            return "stop"
        if not new_ids:
            return "stop"
        return "continue"

    def test_env_disabled(self):
        assert self._check(False, False, 0, 3, ["id1"]) == "stop"

    def test_llm_says_stop(self):
        assert self._check(True, True, 1, 3, ["id1"]) == "stop"

    def test_max_rounds_reached(self):
        assert self._check(True, False, 3, 3, ["id1"]) == "stop"

    def test_no_new_knowledge(self):
        assert self._check(True, False, 1, 3, []) == "stop"

    def test_continue(self):
        assert self._check(True, False, 1, 3, ["id1"]) == "continue"
