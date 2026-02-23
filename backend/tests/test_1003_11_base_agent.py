"""
Tests for BaseAgent + TwoStageDecisionMixin + PrecisionAnswerAgent
TDD Red phase: these tests should fail before implementation.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


class FakeLLM:
    """Fake LLM client for testing."""

    def __init__(self, response=""):
        self.response = response
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append({"system": system_prompt, "user": user_prompt})
        return self.response


class FakeLLMThatFails:
    """LLM that fails N times then succeeds."""

    def __init__(self, fail_count, success_response):
        self.fail_count = fail_count
        self.success_response = success_response
        self.attempt = 0

    def chat(self, system_prompt, user_prompt):
        self.attempt += 1
        if self.attempt <= self.fail_count:
            raise RuntimeError(f"LLM error on attempt {self.attempt}")
        return self.success_response


# ---------------------------------------------------------------------------
# TestBaseAgent
# ---------------------------------------------------------------------------
class TestBaseAgent:

    def _make_agent(self, llm, prompt_config=None):
        from services.blog_generator.agents.base_agent import BaseAgent
        return BaseAgent(llm, "test_agent", prompt_config)

    def test_call_llm_success(self):
        llm = FakeLLM("hello world")
        agent = self._make_agent(llm)
        result = agent.call_llm("say hi", system_prompt="be nice")
        assert result == "hello world"
        assert len(llm.calls) == 1
        assert llm.calls[0]["system"] == "be nice"
        assert llm.calls[0]["user"] == "say hi"

    def test_call_llm_retry_on_error(self):
        llm = FakeLLMThatFails(fail_count=1, success_response="recovered")
        agent = self._make_agent(llm)
        result = agent.call_llm("try this")
        assert result == "recovered"
        assert llm.attempt == 2

    def test_call_llm_json_valid(self):
        llm = FakeLLM(json.dumps({"key": "value"}))
        agent = self._make_agent(llm)
        result = agent.call_llm_json("give json")
        assert result == {"key": "value"}

    def test_call_llm_json_invalid_fallback(self):
        llm = FakeLLM("not json at all")
        agent = self._make_agent(llm)
        result = agent.call_llm_json("give json")
        assert result == {}

    def test_get_prompt(self):
        config = {"greeting": "hello", "farewell": "bye"}
        llm = FakeLLM()
        agent = self._make_agent(llm, prompt_config=config)
        assert agent.get_prompt("greeting") == "hello"
        assert agent.get_prompt("missing", "default_val") == "default_val"

    def test_refresh_config(self):
        llm = FakeLLM()
        agent = self._make_agent(llm)
        # refresh_config is a no-op placeholder; just ensure it doesn't raise
        agent.refresh_config()


# ---------------------------------------------------------------------------
# TestTwoStageDecisionMixin
# ---------------------------------------------------------------------------
class TestTwoStageDecisionMixin:

    def test_run_two_stage_skip(self):
        from services.blog_generator.agents.precision_answer import TwoStageDecisionMixin

        class SkipAgent(TwoStageDecisionMixin):
            def should_execute(self, context):
                return {"should_execute": False, "reason": "not needed"}
            def execute(self, context):
                return {"answer": "should not reach"}

        agent = SkipAgent()
        result = agent.run_two_stage({"question": "test"})
        assert result["executed"] is False
        assert result["result"] is None
        assert result["decision"]["reason"] == "not needed"

    def test_run_two_stage_execute(self):
        from services.blog_generator.agents.precision_answer import TwoStageDecisionMixin

        class GoAgent(TwoStageDecisionMixin):
            def should_execute(self, context):
                return {"should_execute": True, "reason": "needed"}
            def execute(self, context):
                return {"answer": "42"}

        agent = GoAgent()
        result = agent.run_two_stage({"question": "meaning of life"})
        assert result["executed"] is True
        assert result["result"]["answer"] == "42"
        assert result["decision"]["reason"] == "needed"


# ---------------------------------------------------------------------------
# TestPrecisionAnswerAgent
# ---------------------------------------------------------------------------
class TestPrecisionAnswerAgent:

    def test_should_execute_true(self):
        from services.blog_generator.agents.precision_answer import PrecisionAnswerAgent
        llm = FakeLLM(json.dumps({"should_execute": True, "reason": "needs precision"}))
        agent = PrecisionAnswerAgent(llm)
        result = agent.should_execute({"question": "What is 2+2?"})
        assert result["should_execute"] is True
        assert "reason" in result

    def test_should_execute_false(self):
        from services.blog_generator.agents.precision_answer import PrecisionAnswerAgent
        llm = FakeLLM(json.dumps({"should_execute": False, "reason": "open-ended"}))
        agent = PrecisionAnswerAgent(llm)
        result = agent.should_execute({"question": "Tell me about life"})
        assert result["should_execute"] is False

    def test_execute_extracts_answer(self):
        from services.blog_generator.agents.precision_answer import PrecisionAnswerAgent
        llm = FakeLLM(json.dumps({"answer": "4", "confidence": "high"}))
        agent = PrecisionAnswerAgent(llm)
        result = agent.execute({
            "question": "What is 2+2?",
            "detailed_answer": "The sum of 2 and 2 is 4."
        })
        assert result["answer"] == "4"
        assert result["confidence"] == "high"

    def test_run_convenience(self):
        from services.blog_generator.agents.precision_answer import PrecisionAnswerAgent
        # First call: should_execute check returns True
        # Second call: execute returns answer
        responses = [
            json.dumps({"should_execute": True, "reason": "precise"}),
            json.dumps({"answer": "42", "confidence": "high"}),
        ]

        class MultiResponseLLM:
            def __init__(self):
                self.call_idx = 0
            def chat(self, system_prompt, user_prompt):
                resp = responses[self.call_idx]
                self.call_idx += 1
                return resp

        llm = MultiResponseLLM()
        agent = PrecisionAnswerAgent(llm)
        state = {
            "question": "What is the answer?",
            "detailed_answer": "The answer is 42."
        }
        result = agent.run(state)
        assert result["executed"] is True
        assert result["result"]["answer"] == "42"
