"""
37.03 推理引擎 Extended Thinking — 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.orchestrator.thinking_config import (
    AGENT_THINKING_CONFIG,
    should_use_thinking,
    supports_thinking,
)


class TestThinkingConfig:

    def test_planner_enabled(self):
        assert AGENT_THINKING_CONFIG.get("planner") is True

    def test_reviewer_enabled(self):
        assert AGENT_THINKING_CONFIG.get("reviewer") is True

    def test_questioner_enabled(self):
        assert AGENT_THINKING_CONFIG.get("questioner") is True

    def test_writer_disabled(self):
        assert AGENT_THINKING_CONFIG.get("writer") is False

    def test_artist_disabled(self):
        assert AGENT_THINKING_CONFIG.get("artist") is False

    def test_unknown_agent_disabled(self):
        assert AGENT_THINKING_CONFIG.get("unknown_agent") is None


class TestShouldUseThinking:

    def test_enabled_agent_with_global_on(self):
        assert should_use_thinking("planner", global_enabled=True) is True

    def test_enabled_agent_with_global_off(self):
        assert should_use_thinking("planner", global_enabled=False) is False

    def test_disabled_agent_with_global_on(self):
        assert should_use_thinking("writer", global_enabled=True) is False

    def test_unknown_agent(self):
        assert should_use_thinking("unknown", global_enabled=True) is False


class TestSupportsThinking:

    def test_claude_model_supported(self):
        assert supports_thinking("claude-3-5-sonnet-20241022") is True

    def test_claude_opus_supported(self):
        assert supports_thinking("claude-sonnet-4-20250514") is True

    def test_gpt_not_supported(self):
        assert supports_thinking("gpt-4o") is False

    def test_qwen_not_supported(self):
        assert supports_thinking("qwen3-max-preview") is False

    def test_empty_model(self):
        assert supports_thinking("") is False


class TestLLMServiceThinking:
    """测试 LLMService.chat() 的 thinking 参数传递"""

    def test_chat_thinking_param_exists(self):
        """验证 chat() 方法接受 thinking 参数"""
        import inspect
        from services.llm_service import LLMService
        sig = inspect.signature(LLMService.chat)
        assert "thinking" in sig.parameters
        assert "thinking_budget" in sig.parameters
