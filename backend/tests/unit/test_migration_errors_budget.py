"""
TDD 测试：特性 C — 结构化错误回传 + 特性 H — 主动式 Token 预算
基于 102.10.1 细化实现方案 + Phase 4.5 修正（扩展现有 exceptions.py）。
"""
import pytest
from unittest.mock import MagicMock, patch


# ==================== 特性 C：结构化错误 ====================

class TestErrorSeverity:
    """ErrorSeverity 枚举测试"""

    def test_retryable_exists(self):
        from exceptions import ErrorSeverity
        assert ErrorSeverity.RETRYABLE.value == "retryable"

    def test_degradable_exists(self):
        from exceptions import ErrorSeverity
        assert ErrorSeverity.DEGRADABLE.value == "degradable"

    def test_fatal_exists(self):
        from exceptions import ErrorSeverity
        assert ErrorSeverity.FATAL.value == "fatal"


class TestErrorCategory:
    """ErrorCategory 枚举测试"""

    def test_rate_limit(self):
        from exceptions import ErrorCategory
        assert ErrorCategory.LLM_RATE_LIMIT.value == "llm_rate_limit"

    def test_context_overflow(self):
        from exceptions import ErrorCategory
        assert ErrorCategory.LLM_CONTEXT_OVERFLOW.value == "llm_context_overflow"

    def test_timeout(self):
        from exceptions import ErrorCategory
        assert ErrorCategory.LLM_TIMEOUT.value == "llm_timeout"


class TestStructuredError:
    """StructuredError 数据类测试"""

    def test_create_with_required_fields(self):
        from exceptions import StructuredError, ErrorCategory, ErrorSeverity
        err = StructuredError(
            category=ErrorCategory.LLM_RATE_LIMIT,
            severity=ErrorSeverity.RETRYABLE,
            message="Rate limited",
        )
        assert err.category == ErrorCategory.LLM_RATE_LIMIT
        assert err.severity == ErrorSeverity.RETRYABLE

    def test_to_dict(self):
        from exceptions import StructuredError, ErrorCategory, ErrorSeverity
        err = StructuredError(
            category=ErrorCategory.LLM_TIMEOUT,
            severity=ErrorSeverity.RETRYABLE,
            message="Timeout after 600s",
            details={"timeout": 600},
            node_name="writer",
            attempt=3,
        )
        d = err.to_dict()
        assert d["category"] == "llm_timeout"
        assert d["severity"] == "retryable"
        assert d["details"]["timeout"] == 600
        assert d["node_name"] == "writer"

    def test_default_details_empty(self):
        from exceptions import StructuredError, ErrorCategory, ErrorSeverity
        err = StructuredError(
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.FATAL,
            message="Unknown error",
        )
        assert err.details == {}
        assert err.node_name == ""
        assert err.attempt == 0


class TestErrorTrackingMiddleware:
    """ErrorTrackingMiddleware 测试"""

    def test_no_errors_returns_none(self):
        from services.blog_generator.middleware import ErrorTrackingMiddleware
        mw = ErrorTrackingMiddleware()
        state = {"topic": "test"}
        result = mw.after_node(state, "researcher")
        assert result is None

    def test_collects_node_errors(self):
        from services.blog_generator.middleware import ErrorTrackingMiddleware
        mw = ErrorTrackingMiddleware()
        state = {
            "_node_errors": [{"category": "llm_timeout", "message": "timeout"}],
            "error_history": [],
        }
        result = mw.after_node(state, "writer")
        assert result is not None
        assert len(result["error_history"]) == 1
        assert result["_node_errors"] == []

    def test_appends_to_existing_history(self):
        from services.blog_generator.middleware import ErrorTrackingMiddleware
        mw = ErrorTrackingMiddleware()
        state = {
            "_node_errors": [{"category": "llm_rate_limit"}],
            "error_history": [{"category": "llm_timeout"}],
        }
        result = mw.after_node(state, "reviewer")
        assert len(result["error_history"]) == 2


# ==================== 特性 H：TokenBudgetMiddleware ====================

class TestTokenBudgetMiddleware:
    """主动式 Token 预算管理测试"""

    def test_writer_gets_largest_budget(self):
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mock_compressor = MagicMock()
        mw = TokenBudgetMiddleware(compressor=mock_compressor, total_budget=500000)
        assert mw.NODE_BUDGET_WEIGHTS["writer"] == 0.35
        assert mw.NODE_BUDGET_WEIGHTS["writer"] > mw.NODE_BUDGET_WEIGHTS["researcher"]

    def test_before_node_returns_budget(self):
        """正常情况下返回节点预算"""
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mock_compressor = MagicMock()
        mw = TokenBudgetMiddleware(compressor=mock_compressor, total_budget=500000)
        result = mw.before_node({"topic": "test"}, "researcher")
        assert result is not None
        assert "_node_budget" in result
        assert result["_node_budget"] == int(500000 * 0.10)

    def test_triggers_compression_when_budget_low(self):
        """预算不足时触发压缩"""
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mock_compressor = MagicMock()
        mock_compressor.apply_strategy.return_value = [{"role": "user", "content": "compressed"}]

        mw = TokenBudgetMiddleware(compressor=mock_compressor, total_budget=100000)
        mw._used_tokens = 95000  # 已用 95%

        result = mw.before_node({"_messages": [{"role": "user", "content": "long..."}]}, "writer")
        assert result.get("_budget_warning") is True
        mock_compressor.apply_strategy.assert_called_once()

    def test_after_node_tracks_usage(self):
        """after_node 记录 token 消耗"""
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mock_compressor = MagicMock()
        mock_tracker = MagicMock()
        mock_tracker.last_call = MagicMock(total_tokens=1500)

        mw = TokenBudgetMiddleware(
            compressor=mock_compressor,
            token_tracker=mock_tracker,
            total_budget=500000,
        )
        mw.after_node({}, "researcher")
        assert mw._used_tokens == 1500

    def test_disabled_via_env(self):
        """TOKEN_BUDGET_ENABLED=false 时跳过"""
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mock_compressor = MagicMock()

        with patch.dict("os.environ", {"TOKEN_BUDGET_ENABLED": "false"}):
            mw = TokenBudgetMiddleware(compressor=mock_compressor, total_budget=100)
            mw._used_tokens = 99  # 几乎耗尽
            result = mw.before_node({}, "writer")
            # 禁用时不应触发压缩
            mock_compressor.apply_strategy.assert_not_called()

    def test_default_weight_for_unknown_node(self):
        """未知节点使用默认权重"""
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mock_compressor = MagicMock()
        mw = TokenBudgetMiddleware(compressor=mock_compressor, total_budget=500000)
        result = mw.before_node({}, "unknown_node")
        assert result["_node_budget"] == int(500000 * 0.05)
