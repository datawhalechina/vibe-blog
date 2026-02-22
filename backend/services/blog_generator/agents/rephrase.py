"""
RephraseAgent - multi-round topic optimization agent.

Supports iterative topic refinement through conversation with LLM,
with satisfaction checking via keyword matching and LLM fallback.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

MAX_REPHRASE_ROUNDS = 3

SATISFIED_KEYWORDS = ["ok", "yes", "好", "可以", "满意", "不错", "行", "确认", "同意"]
CONTINUE_KEYWORDS = ["改", "换", "调整", "不", "需要", "希望", "应该", "重新"]


class RephraseAgent:
    """Multi-round topic optimization agent.

    Iteratively refines a user's topic through LLM-powered rephrasing,
    tracking conversation history across rounds.
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.conversation_history = []

    def reset_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def _format_history(self):
        """Format conversation history as text for LLM context."""
        if not self.conversation_history:
            return ""
        lines = []
        for entry in self.conversation_history:
            role = entry["role"]
            content = entry["content"]
            if role == "user":
                lines.append(f"User: {content}")
            else:
                lines.append(f"Assistant: {content}")
        return "\n".join(lines)

    def rephrase(self, user_input, iteration=0):
        """Rephrase/optimize a topic through LLM conversation.

        Args:
            user_input: The user's topic or feedback text.
            iteration: Round number. 0 resets history.

        Returns:
            dict with "topic" (str) and "iteration" (int).
        """
        if iteration == 0:
            self.reset_history()

        self.conversation_history.append({
            "role": "user",
            "content": user_input,
        })

        system_prompt = (
            "You are a topic optimization assistant. "
            "Given the user's input, refine it into a clear, engaging topic. "
            "Return JSON with a single key 'topic'."
        )
        history_text = self._format_history()
        user_prompt = f"{user_input}\n\nConversation history:\n{history_text}" if history_text else user_input

        try:
            raw = self.llm.chat(system_prompt, user_prompt)
            parsed = json.loads(raw)
            topic = parsed.get("topic", user_input)
        except (json.JSONDecodeError, Exception):
            topic = user_input

        self.conversation_history.append({
            "role": "assistant",
            "content": topic,
        })

        return {"topic": topic, "iteration": iteration}

    def check_satisfaction(self, topic, feedback):
        """Check if the user is satisfied with the current topic.

        Uses keyword matching first, falls back to LLM judgment.

        Args:
            topic: The current topic string.
            feedback: The user's feedback text.

        Returns:
            dict with "user_satisfied" (bool) and "reason" (str).
        """
        feedback_lower = feedback.lower().strip()

        def _has_keyword(text, kw):
            """Match keyword: word-boundary for ASCII, substring for CJK."""
            if kw.isascii():
                return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
            return kw in text

        # Check continue keywords first (negation takes priority)
        for kw in CONTINUE_KEYWORDS:
            if _has_keyword(feedback_lower, kw):
                return {"user_satisfied": False, "reason": f"keyword_match: {kw}"}

        # Check satisfied keywords
        for kw in SATISFIED_KEYWORDS:
            if _has_keyword(feedback_lower, kw):
                return {"user_satisfied": True, "reason": f"keyword_match: {kw}"}

        # Fallback: ask LLM
        try:
            system_prompt = (
                "Judge whether the user is satisfied with the topic. "
                "Return JSON: {\"user_satisfied\": true/false, \"reason\": \"...\"}"
            )
            user_prompt = f"Topic: {topic}\nUser feedback: {feedback}"
            raw = self.llm.chat(system_prompt, user_prompt)
            parsed = json.loads(raw)
            return {
                "user_satisfied": bool(parsed.get("user_satisfied", False)),
                "reason": parsed.get("reason", "llm_judgment"),
            }
        except (json.JSONDecodeError, Exception):
            # Final fallback: keyword heuristic failed, LLM failed, assume not satisfied
            return {"user_satisfied": False, "reason": "unable_to_determine"}
