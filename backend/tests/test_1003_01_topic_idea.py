"""
TDD 测试 — 1003.01 四阶段选题生成 TopicIdeaAgent
"""

import json
import sys
import os
import pytest

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeLLM:
    """模拟 LLM 客户端"""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self._call_count = 0

    def chat(self, messages, response_format=None, **kwargs):
        if self._call_count >= len(self._responses):
            return self._responses[-1] if self._responses else ""
        resp = self._responses[self._call_count]
        self._call_count += 1
        return resp


# --- extract_knowledge_points ---
class TestExtractKnowledgePoints:
    def test_extracts_points_from_search_results(self):
        fake_response = json.dumps({
            "knowledge_points": [
                {"knowledge_point": "Transformer Attention", "description": "Self-attention mechanism in transformer architecture"},
                {"knowledge_point": "LoRA Fine-tuning", "description": "Low-rank adaptation for efficient LLM fine-tuning"},
            ]
        })
        llm = FakeLLM([fake_response])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        points = agent.extract_knowledge_points(
            topic="LLM 微调技术",
            search_results=[{"title": "LoRA paper", "snippet": "Low-rank adaptation..."}],
        )
        assert len(points) >= 1
        assert all("knowledge_point" in p and "description" in p for p in points)

    def test_returns_empty_on_no_results(self):
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(FakeLLM([]))
        points = agent.extract_knowledge_points("test", [])
        assert points == []


# --- loose_filter ---
class TestLooseFilter:
    def test_filters_out_trivial_points(self):
        input_points = [
            {"knowledge_point": "1+1=2", "description": "Basic arithmetic"},
            {"knowledge_point": "Transformer Attention", "description": "Self-attention mechanism"},
        ]
        fake_response = json.dumps({
            "filtered_points": [
                {"knowledge_point": "Transformer Attention", "description": "Self-attention mechanism"},
            ]
        })
        llm = FakeLLM([fake_response])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.loose_filter(input_points)
        assert len(result) >= 1

    def test_returns_original_on_json_error(self):
        input_points = [{"knowledge_point": "Test", "description": "Test desc"}]
        llm = FakeLLM(["not valid json"])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.loose_filter(input_points)
        assert result == input_points

    def test_single_point_passthrough(self):
        """单个知识点直接通过，不调用 LLM"""
        input_points = [{"knowledge_point": "Only", "description": "Only point"}]
        llm = FakeLLM([])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.loose_filter(input_points)
        assert result == input_points
        assert llm._call_count == 0


# --- strict_filter ---
class TestStrictFilter:
    def test_keeps_at_least_one_idea(self):
        point = {"knowledge_point": "Test", "description": "Test description"}
        ideas = ["idea1", "idea2", "idea3", "idea4", "idea5"]
        fake_response = json.dumps({
            "kept_ideas": ["idea1"],
            "rejected_ideas": ["idea2", "idea3", "idea4", "idea5"],
            "reasons": {},
        })
        llm = FakeLLM([fake_response])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.strict_filter(point, ideas)
        assert len(result) >= 1

    def test_single_idea_passthrough(self):
        point = {"knowledge_point": "Test", "description": "Test description"}
        ideas = ["only_idea"]
        llm = FakeLLM([])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.strict_filter(point, ideas)
        assert result == ["only_idea"]
        assert llm._call_count == 0

    def test_fallback_on_all_rejected(self):
        point = {"knowledge_point": "Test", "description": "Test description"}
        ideas = ["idea1", "idea2", "idea3"]
        fake_response = json.dumps({
            "kept_ideas": [],
            "rejected_ideas": ["idea1", "idea2", "idea3"],
            "reasons": {},
        })
        llm = FakeLLM([fake_response])
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.strict_filter(point, ideas)
        assert len(result) >= 1


# --- generate_ideas 端到端 ---
class TestGenerateIdeasE2E:
    def test_full_pipeline_returns_ideas(self):
        responses = [
            # extract_knowledge_points
            json.dumps({"knowledge_points": [
                {"knowledge_point": "RAG", "description": "Retrieval-augmented generation for LLMs"},
                {"knowledge_point": "LoRA", "description": "Low-rank adaptation for efficient fine-tuning"},
            ]}),
            # loose_filter (2 points → LLM called)
            json.dumps({"filtered_points": [
                {"knowledge_point": "RAG", "description": "Retrieval-augmented generation for LLMs"},
            ]}),
            # explore_ideas for RAG
            json.dumps({"research_ideas": [
                "Hybrid RAG with knowledge graphs",
                "RAG evaluation benchmarks",
                "Multi-modal RAG systems",
                "RAG for code generation",
                "Adaptive retrieval strategies",
            ]}),
            # strict_filter for RAG
            json.dumps({
                "kept_ideas": ["Hybrid RAG with knowledge graphs", "RAG evaluation benchmarks"],
                "rejected_ideas": ["Multi-modal RAG systems", "RAG for code generation", "Adaptive retrieval strategies"],
                "reasons": {},
            }),
            # generate_statement
            "## RAG\n\n**Research Ideas:**\n\n### 1. Hybrid RAG\n\nCombining knowledge graphs...",
        ]
        llm = FakeLLM(responses)
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(llm)

        result = agent.generate_ideas({
            "topic": "RAG 技术",
            "search_results": [{"title": "RAG paper", "snippet": "..."}],
        })

        assert len(result["topic_ideas"]) >= 1
        assert result["topic_statement"] is not None
        assert result["topic_statement"] != ""
        assert len(result["knowledge_points"]) >= 1

    def test_empty_search_results_returns_empty(self):
        from services.blog_generator.agents.topic_idea import TopicIdeaAgent
        agent = TopicIdeaAgent(FakeLLM([]))

        result = agent.generate_ideas({"topic": "test", "search_results": []})
        assert result["topic_ideas"] == []
        assert result["knowledge_points"] == []
