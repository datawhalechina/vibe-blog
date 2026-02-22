"""
Tests for RephraseAgent - multi-round topic optimization agent.
TDD: RED phase - tests written before implementation.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.blog_generator.agents.rephrase import RephraseAgent, MAX_REPHRASE_ROUNDS


class FakeLLM:
    def __init__(self, response=""):
        self.response = response
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append({"system": system_prompt, "user": user_prompt})
        return self.response


# ---------------------------------------------------------------------------
# TestRephrase
# ---------------------------------------------------------------------------
class TestRephrase:
    def test_returns_topic(self):
        """rephrase() should return a dict with 'topic' parsed from LLM JSON."""
        fake = FakeLLM(response=json.dumps({"topic": "Optimized Topic"}))
        agent = RephraseAgent(fake)
        result = agent.rephrase("raw input")
        assert result["topic"] == "Optimized Topic"
        assert result["iteration"] == 0

    def test_iteration_zero_resets_history(self):
        """iteration=0 should clear conversation history."""
        fake = FakeLLM(response=json.dumps({"topic": "T1"}))
        agent = RephraseAgent(fake)
        # First call builds history
        agent.rephrase("first", iteration=0)
        assert len(agent.conversation_history) > 0
        # Second call with iteration=0 should reset before proceeding
        agent.rephrase("second", iteration=0)
        # History should only contain entries from the latest call
        user_entries = [h for h in agent.conversation_history if h["role"] == "user"]
        assert len(user_entries) == 1
        assert "second" in user_entries[0]["content"]

    def test_fallback_on_invalid_json(self):
        """When LLM returns non-JSON, fallback to raw user_input as topic."""
        fake = FakeLLM(response="not valid json at all")
        agent = RephraseAgent(fake)
        result = agent.rephrase("my raw topic")
        assert result["topic"] == "my raw topic"

    def test_multi_round_history(self):
        """Multiple rounds should accumulate history entries."""
        fake = FakeLLM(response=json.dumps({"topic": "Round1"}))
        agent = RephraseAgent(fake)
        agent.rephrase("input1", iteration=0)

        fake.response = json.dumps({"topic": "Round2"})
        agent.rephrase("input2", iteration=1)

        # Should have 2 user + 2 assistant entries
        assert len(agent.conversation_history) == 4


# ---------------------------------------------------------------------------
# TestCheckSatisfaction
# ---------------------------------------------------------------------------
class TestCheckSatisfaction:
    def test_satisfied_keywords(self):
        """Keywords like 'ok', 'yes', '好' should return satisfied=True."""
        fake = FakeLLM(response="")  # LLM won't be called for keyword match
        agent = RephraseAgent(fake)
        for word in ["ok", "yes", "好", "可以", "满意"]:
            result = agent.check_satisfaction("some topic", word)
            assert result["user_satisfied"] is True, f"Expected satisfied for '{word}'"
            assert "reason" in result

    def test_continue_keywords(self):
        """Keywords like '改', '换', '不' should return satisfied=False."""
        fake = FakeLLM(response="")
        agent = RephraseAgent(fake)
        for word in ["改一下", "换个方向", "不太好"]:
            result = agent.check_satisfaction("some topic", word)
            assert result["user_satisfied"] is False, f"Expected not satisfied for '{word}'"
            assert "reason" in result

    def test_llm_based_satisfaction(self):
        """When no keyword matches, should call LLM to judge."""
        llm_response = json.dumps({"user_satisfied": True, "reason": "LLM says yes"})
        fake = FakeLLM(response=llm_response)
        agent = RephraseAgent(fake)
        result = agent.check_satisfaction("some topic", "this looks interesting to me")
        assert result["user_satisfied"] is True
        assert result["reason"] == "LLM says yes"
        assert len(fake.calls) == 1  # LLM was actually called


# ---------------------------------------------------------------------------
# TestRephraseEdgeCases
# ---------------------------------------------------------------------------
class TestRephraseEdgeCases:
    def test_empty_input(self):
        """Empty input should still return a result with fallback."""
        fake = FakeLLM(response=json.dumps({"topic": ""}))
        agent = RephraseAgent(fake)
        result = agent.rephrase("")
        assert "topic" in result
        assert "iteration" in result

    def test_max_rounds_tracking(self):
        """MAX_REPHRASE_ROUNDS should be 3."""
        assert MAX_REPHRASE_ROUNDS == 3
