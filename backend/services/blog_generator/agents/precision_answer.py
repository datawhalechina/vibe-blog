"""
TwoStageDecisionMixin + PrecisionAnswerAgent

Two-stage pattern: first decide whether to execute, then execute.
PrecisionAnswerAgent uses LLM to judge if a question needs a precise
answer, then extracts one from a detailed answer.
"""

import json
import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TwoStageDecisionMixin:
    """Mixin that adds a should_execute / execute two-stage workflow."""

    def should_execute(self, context: dict) -> dict:
        raise NotImplementedError

    def execute(self, context: dict) -> dict:
        raise NotImplementedError

    def run_two_stage(self, context: dict) -> dict:
        decision = self.should_execute(context)
        if not decision.get("should_execute", False):
            return {"executed": False, "decision": decision, "result": None}
        result = self.execute(context)
        return {"executed": True, "decision": decision, "result": result}


class PrecisionAnswerAgent(BaseAgent, TwoStageDecisionMixin):
    """Agent that decides whether a question needs a precise answer,
    then extracts one from a detailed answer."""

    def __init__(self, llm_client):
        super().__init__(llm_client, "precision_answer")

    def should_execute(self, context: dict) -> dict:
        """Ask LLM whether the question requires a precise answer."""
        question = context.get("question", "")
        system_prompt = (
            "You are a question classifier. Determine if the question requires "
            "a precise, factual answer. Respond in JSON: "
            '{"should_execute": true/false, "reason": "..."}'
        )
        user_prompt = f"Question: {question}"
        return self.call_llm_json(user_prompt, system_prompt)

    def execute(self, context: dict) -> dict:
        """Extract a precise answer from the detailed answer."""
        question = context.get("question", "")
        detailed = context.get("detailed_answer", "")
        system_prompt = (
            "Extract the precise answer from the detailed text. "
            "Respond in JSON: "
            '{"answer": "...", "confidence": "high/medium/low"}'
        )
        user_prompt = f"Question: {question}\n\nDetailed answer: {detailed}"
        return self.call_llm_json(user_prompt, system_prompt)

    def run(self, state: dict) -> dict:
        """Convenience method: build context from state and run two-stage."""
        context = {
            "question": state.get("question", ""),
            "detailed_answer": state.get("detailed_answer", ""),
        }
        return self.run_two_stage(context)
