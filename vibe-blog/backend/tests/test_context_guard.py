"""
37.33 上下文长度动态估算与自动回退 — 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.context_guard import (
    estimate_tokens,
    _estimate_by_chars,
    get_context_limit,
    get_safe_input_limit,
    ContextGuard,
    MODEL_CONTEXT_LIMITS,
)


# ============ estimate_tokens 测试 ============

class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_char_method_english(self):
        text = "a" * 400
        tokens = estimate_tokens(text, method="char")
        assert tokens == 100  # 400 / 4

    def test_char_method_chinese(self):
        text = "你" * 150
        tokens = estimate_tokens(text, method="char")
        assert tokens == 100  # 150 / 1.5

    def test_auto_method_returns_positive(self):
        text = "Hello world, this is a test sentence."
        tokens = estimate_tokens(text, method="auto")
        assert tokens > 0

    def test_tiktoken_fallback_on_import_error(self):
        """tiktoken 不可用时降级为字符估算"""
        with patch.dict('sys.modules', {'tiktoken': None}):
            # 清除缓存的 encoder
            if hasattr(estimate_tokens, '_encoder'):
                delattr(estimate_tokens, '_encoder')
            text = "a" * 400
            tokens = estimate_tokens(text, method="auto")
            assert tokens > 0


# ============ _estimate_by_chars 测试 ============

class TestEstimateByChars:
    def test_pure_english(self):
        assert _estimate_by_chars("a" * 100) == 25

    def test_pure_chinese(self):
        assert _estimate_by_chars("你" * 150) == 100

    def test_mixed(self):
        text = "你好" + "a" * 40  # 2 中文 + 40 英文
        tokens = _estimate_by_chars(text)
        expected = int(2 / 1.5 + 40 / 4)  # 1 + 10 = 11
        assert tokens == expected


# ============ get_context_limit 测试 ============

class TestGetContextLimit:
    def test_exact_match(self):
        assert get_context_limit("gpt-4o") == 128_000

    def test_prefix_match(self):
        assert get_context_limit("gpt-4o-2024-08-06") == 128_000

    def test_qwen_prefix(self):
        assert get_context_limit("qwen3-max-preview") == 128_000

    def test_unknown_model_default(self):
        limit = get_context_limit("unknown-model-xyz")
        assert limit == 128_000

    def test_deepseek(self):
        assert get_context_limit("deepseek-chat") == 64_000


# ============ get_safe_input_limit 测试 ============

class TestGetSafeInputLimit:
    def test_basic(self):
        limit = get_safe_input_limit("gpt-4o", max_output_tokens=8192)
        # 128000 * 0.85 - 8192 - 1000 = 108800 - 9192 = 99608
        assert limit > 90000
        assert limit < 110000

    def test_minimum_floor(self):
        """即使模型窗口很小，也至少返回 4096"""
        limit = get_safe_input_limit("gpt-4", max_output_tokens=8192)
        assert limit >= 4096


# ============ ContextGuard.check 测试 ============

class TestContextGuardCheck:
    def test_safe_messages(self):
        guard = ContextGuard("gpt-4o", max_output_tokens=4096)
        messages = [{"role": "user", "content": "Hello"}]
        result = guard.check(messages)
        assert result["is_safe"] is True
        assert result["estimated_tokens"] > 0
        assert result["overflow_tokens"] < 0

    def test_oversized_messages(self):
        guard = ContextGuard("gpt-4", max_output_tokens=4096)
        # gpt-4 只有 8192 上下文，构造超长内容
        messages = [{"role": "user", "content": "x" * 100000}]
        result = guard.check(messages)
        assert result["is_safe"] is False
        assert result["overflow_tokens"] > 0

    def test_list_content_format(self):
        """支持 Anthropic 格式的 list content"""
        guard = ContextGuard("gpt-4o")
        messages = [{"role": "user", "content": [{"text": "Hello"}, {"text": " world"}]}]
        result = guard.check(messages)
        assert result["estimated_tokens"] > 0


# ============ ContextGuard.trim_prompt 测试 ============

class TestContextGuardTrimPrompt:
    def test_no_trim_needed(self):
        guard = ContextGuard("gpt-4o", max_output_tokens=4096)
        prompt = "{instructions}\n{research}"
        sections = {"instructions": "Write a blog", "research": "Some data"}
        result, info = guard.trim_prompt(prompt, sections)
        assert info["trimmed"] is False
        assert "Write a blog" in result
        assert "Some data" in result

    def test_full_section_removal(self):
        """超限时应整段移除低优先级内容"""
        guard = ContextGuard("gpt-4", max_output_tokens=4096)
        # gpt-4 safe limit 很小，构造超长 research
        long_research = "data " * 10000
        prompt = "{instructions}\n{research}"
        sections = {"instructions": "Write", "research": long_research}
        result, info = guard.trim_prompt(prompt, sections, priority=["research", "instructions"])
        assert info["trimmed"] is True
        assert len(info["trimmed_sections"]) > 0
        assert info["trimmed_sections"][0]["section"] == "research"

    def test_partial_truncation(self):
        """部分裁剪应保留前 N 个字符"""
        guard = ContextGuard("gpt-4", max_output_tokens=4096)
        # 构造刚好需要部分裁剪的场景
        medium_research = "data " * 2000
        prompt = "{research}"
        sections = {"research": medium_research}
        result, info = guard.trim_prompt(prompt, sections, priority=["research"])
        if info["trimmed"]:
            assert "已截断" in result or "已裁剪" in result

    def test_custom_priority(self):
        """自定义优先级应生效"""
        guard = ContextGuard("gpt-4", max_output_tokens=4096)
        long_content = "x " * 10000
        prompt = "{a}\n{b}"
        sections = {"a": long_content, "b": long_content}
        _, info = guard.trim_prompt(prompt, sections, priority=["b", "a"])
        if info["trimmed"] and info["trimmed_sections"]:
            assert info["trimmed_sections"][0]["section"] == "b"
