"""
BaseAgent -- optional base class for blog generator agents.

Provides common LLM calling utilities (plain text + JSON), prompt config
access, and a logger. Not abstract -- agents may inherit or not.
"""

import json
import logging
import time


class BaseAgent:
    """Optional base class that standardises LLM interaction patterns."""

    def __init__(self, llm_client, agent_name: str, prompt_config: dict = None):
        self.llm = llm_client
        self.agent_name = agent_name
        self._prompt_config = prompt_config or {}
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def call_llm(self, user_prompt: str, system_prompt: str = None, max_retries: int = 2) -> str:
        """Call LLM with retry logic. Returns the raw string response."""
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                result = self.llm.chat(system_prompt, user_prompt)
                self.logger.debug(
                    "[%s] LLM call succeeded on attempt %d", self.agent_name, attempt
                )
                return result
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "[%s] LLM call failed (attempt %d/%d): %s",
                    self.agent_name, attempt, max_retries, exc,
                )
                if attempt < max_retries:
                    time.sleep(0.05 * attempt)
        raise last_error  # type: ignore[misc]

    def call_llm_json(self, user_prompt: str, system_prompt: str = None, max_retries: int = 2) -> dict:
        """Call LLM and parse the response as JSON. Returns {} on parse failure."""
        for attempt in range(1, max_retries + 1):
            try:
                raw = self.call_llm(user_prompt, system_prompt, max_retries=max_retries)
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                self.logger.warning(
                    "[%s] JSON parse failed (attempt %d/%d)",
                    self.agent_name, attempt, max_retries,
                )
        return {}

    # ------------------------------------------------------------------
    # Prompt config
    # ------------------------------------------------------------------

    def get_prompt(self, key: str, fallback: str = "") -> str:
        """Retrieve a prompt template from the config dict."""
        return self._prompt_config.get(key, fallback)

    def refresh_config(self):
        """Placeholder for hot-reload of prompt config."""
        pass
