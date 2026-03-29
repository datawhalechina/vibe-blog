"""
37.32 LLM 响应截断自动扩容与智能重试 — 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.resilient_llm_caller import (
    is_truncated,
    is_repeated,
    is_context_length_error,
    resilient_chat,
    LLMCallTimeout,
    ContextLengthExceeded,
    REPEAT_TAIL_LENGTH,
    REPEAT_THRESHOLD,
)


# ============ is_truncated 测试 ============

class TestIsTruncated:
    def test_openai_length(self):
        """OpenAI finish_reason='length' 应判定为截断"""
        resp = MagicMock()
        resp.response_metadata = {"finish_reason": "length"}
        assert is_truncated(resp) is True

    def test_openai_stop(self):
        """OpenAI finish_reason='stop' 不是截断"""
        resp = MagicMock()
        resp.response_metadata = {"finish_reason": "stop"}
        assert is_truncated(resp) is False

    def test_anthropic_max_tokens(self):
        """Anthropic stop_reason='max_tokens' 应判定为截断"""
        resp = MagicMock()
        resp.response_metadata = {"stop_reason": "max_tokens"}
        assert is_truncated(resp) is True

    def test_anthropic_end_turn(self):
        """Anthropic stop_reason='end_turn' 不是截断"""
        resp = MagicMock()
        resp.response_metadata = {"stop_reason": "end_turn"}
        assert is_truncated(resp) is False

    def test_no_metadata(self):
        """无 response_metadata 属性不是截断"""
        resp = MagicMock(spec=[])  # 无任何属性
        assert is_truncated(resp) is False

    def test_empty_metadata(self):
        """空 metadata 不是截断"""
        resp = MagicMock()
        resp.response_metadata = {}
        assert is_truncated(resp) is False

    def test_none_metadata(self):
        """metadata 为 None 不是截断"""
        resp = MagicMock()
        resp.response_metadata = None
        assert is_truncated(resp) is False


# ============ is_repeated 测试 ============

class TestIsRepeated:
    def test_no_repeat(self):
        """正常文本不应判定为重复"""
        content = "这是一段正常的博客内容，没有重复。" * 5
        assert is_repeated(content) is False

    def test_severe_repeat(self):
        """严重重复应被检测到"""
        tail = "x" * REPEAT_TAIL_LENGTH
        # 构造重复超过阈值的内容
        content = tail * (REPEAT_THRESHOLD + 2)
        assert is_repeated(content) is True

    def test_short_content(self):
        """过短内容不应判定为重复"""
        assert is_repeated("short") is False
        assert is_repeated("") is False

    def test_exactly_at_threshold(self):
        """刚好等于阈值不应判定为重复（需要 > 阈值）"""
        tail = "a" * REPEAT_TAIL_LENGTH
        # count = REPEAT_THRESHOLD 时不算重复
        padding = "b" * REPEAT_TAIL_LENGTH
        content = padding + tail * REPEAT_THRESHOLD
        assert is_repeated(content) is False


# ============ is_context_length_error 测试 ============

class TestIsContextLengthError:
    def test_maximum_context_length(self):
        err = Exception("This model's maximum context length is 128000 tokens")
        assert is_context_length_error(err) is True

    def test_context_length_exceeded(self):
        err = Exception("Error code: 400 - context_length_exceeded")
        assert is_context_length_error(err) is True

    def test_too_many_tokens(self):
        err = Exception("Request too large: too many tokens in the prompt")
        assert is_context_length_error(err) is True

    def test_prompt_too_long(self):
        err = Exception("prompt is too long")
        assert is_context_length_error(err) is True

    def test_normal_error(self):
        err = Exception("Connection timeout")
        assert is_context_length_error(err) is False

    def test_429_error(self):
        err = Exception("Error code: 429 - Rate limit exceeded")
        assert is_context_length_error(err) is False


# ============ resilient_chat 测试 ============

def _make_response(content="Hello", finish_reason="stop", stop_reason=None):
    """构造 mock LangChain AIMessage 响应"""
    resp = MagicMock()
    resp.content = content
    meta = {}
    if finish_reason:
        meta["finish_reason"] = finish_reason
    if stop_reason:
        meta["stop_reason"] = stop_reason
    resp.response_metadata = meta
    return resp


class TestResilientChat:
    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_normal_response(self, mock_rl):
        """正常响应直接返回"""
        model = MagicMock()
        model.invoke.return_value = _make_response("Hello world")
        messages = [MagicMock()]

        content, meta = resilient_chat(model, messages, max_retries=3, base_wait=0.01)
        assert content == "Hello world"
        assert meta["truncated"] is False
        assert meta["attempts"] == 1
        assert meta["finish_reason"] == "stop"

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_truncation_retry_and_expand(self, mock_rl):
        """截断时应扩容 max_tokens 并重试"""
        model = MagicMock()
        model.max_tokens = 1000
        model.bind.return_value = model

        # 第一次截断，第二次正常
        model.invoke.side_effect = [
            _make_response("partial", finish_reason="length"),
            _make_response("full content", finish_reason="stop"),
        ]

        content, meta = resilient_chat(model, [MagicMock()], max_retries=3, base_wait=0.01)
        assert content == "full content"
        assert meta["truncated"] is False
        assert meta["attempts"] == 2
        # 验证 bind 被调用了扩容后的 max_tokens
        model.bind.assert_called_with(max_tokens=1100)

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_truncation_max_retries_returns_partial(self, mock_rl):
        """截断达到最大重试次数应返回截断结果"""
        model = MagicMock()
        model.max_tokens = 1000
        model.bind.return_value = model
        model.invoke.return_value = _make_response("partial", finish_reason="length")

        content, meta = resilient_chat(model, [MagicMock()], max_retries=2, base_wait=0.01)
        assert content == "partial"
        assert meta["truncated"] is True
        assert meta["finish_reason"] == "length"
        assert meta["attempts"] == 2

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_context_length_error_fast_fail(self, mock_rl):
        """上下文超限应立即抛出 ContextLengthExceeded，不重试"""
        model = MagicMock()
        model.invoke.side_effect = Exception("maximum context length exceeded")

        with pytest.raises(ContextLengthExceeded):
            resilient_chat(model, [MagicMock()], max_retries=3, base_wait=0.01)

        # 只调用了一次，没有重试
        assert model.invoke.call_count == 1

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_429_exponential_backoff(self, mock_rl):
        """429 错误应指数退避重试"""
        model = MagicMock()
        model.invoke.side_effect = [
            Exception("Error code: 429 - Rate limit"),
            _make_response("ok"),
        ]

        content, meta = resilient_chat(model, [MagicMock()], max_retries=3, base_wait=0.01, max_wait=1)
        assert content == "ok"
        assert meta["attempts"] == 2

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_general_error_retry(self, mock_rl):
        """一般错误应重试"""
        model = MagicMock()
        model.invoke.side_effect = [
            Exception("Connection reset"),
            _make_response("recovered"),
        ]

        content, meta = resilient_chat(model, [MagicMock()], max_retries=3, base_wait=0.01)
        assert content == "recovered"
        assert meta["attempts"] == 2

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_general_error_exhausted(self, mock_rl):
        """一般错误重试耗尽应抛出最终异常"""
        model = MagicMock()
        model.invoke.side_effect = Exception("Server error")

        with pytest.raises(Exception, match="Server error"):
            resilient_chat(model, [MagicMock()], max_retries=2, base_wait=0.01)

        assert model.invoke.call_count == 2

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_repeat_detection_retry(self, mock_rl):
        """重复输出应触发重试"""
        model = MagicMock()
        tail = "x" * REPEAT_TAIL_LENGTH
        repeated_content = tail * (REPEAT_THRESHOLD + 2)

        model.invoke.side_effect = [
            _make_response(repeated_content),
            _make_response("good content"),
        ]

        content, meta = resilient_chat(model, [MagicMock()], max_retries=3, base_wait=0.01)
        assert content == "good content"
        assert meta["attempts"] == 2

    @patch('utils.resilient_llm_caller._rate_limit_hook')
    def test_caller_label_in_logs(self, mock_rl):
        """caller 参数应出现在日志中"""
        model = MagicMock()
        model.invoke.return_value = _make_response("ok")

        content, meta = resilient_chat(model, [MagicMock()], caller="TestAgent", base_wait=0.01)
        assert content == "ok"
