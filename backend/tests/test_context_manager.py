"""
上下文压缩增强 — 统一 ContextManager + CompressionConfig 单元测试

TDD Red: 先写测试，再实现代码。
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============ CompressionTrigger 测试 ============


class TestCompressionTrigger:
    """多维度触发条件测试"""

    def test_token_trigger_met(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="tokens", value=10000)
        assert trigger.is_met(token_count=12000, message_count=5,
                              context_limit=128000, usage_ratio=0.1)

    def test_token_trigger_not_met(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="tokens", value=10000)
        assert not trigger.is_met(token_count=5000, message_count=5,
                                  context_limit=128000, usage_ratio=0.04)

    def test_fraction_trigger(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="fraction", value=0.8)
        assert trigger.is_met(token_count=105000, message_count=10,
                              context_limit=128000, usage_ratio=0.82)

    def test_fraction_trigger_not_met(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="fraction", value=0.8)
        assert not trigger.is_met(token_count=50000, message_count=10,
                                  context_limit=128000, usage_ratio=0.39)

    def test_message_trigger(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="messages", value=50)
        assert trigger.is_met(token_count=1000, message_count=60,
                              context_limit=128000, usage_ratio=0.01)
    def test_message_trigger_not_met(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="messages", value=50)
        assert not trigger.is_met(token_count=1000, message_count=10,
                                  context_limit=128000, usage_ratio=0.01)

    def test_ratio_trigger_backward_compat(self):
        """确保与 vibe-blog 现有 usage_ratio 逻辑兼容"""
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="ratio", value=0.70)
        assert trigger.is_met(token_count=0, message_count=0,
                              context_limit=0, usage_ratio=0.75)

    def test_ratio_trigger_not_met(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="ratio", value=0.70)
        assert not trigger.is_met(token_count=0, message_count=0,
                                  context_limit=0, usage_ratio=0.50)

    def test_unknown_type_returns_false(self):
        from utils.context_manager import CompressionTrigger
        trigger = CompressionTrigger(type="unknown", value=0.5)
        assert not trigger.is_met(token_count=100, message_count=100,
                                  context_limit=128000, usage_ratio=0.99)


# ============ CompressionConfig 测试 ============


class TestCompressionConfig:
    """配置化测试"""

    def test_default_config(self):
        from utils.context_manager import CompressionConfig
        config = CompressionConfig()
        assert config.enabled is True
        assert len(config.triggers) >= 1
        assert config.summarization_enabled is False

    def test_from_env_defaults(self):
        from utils.context_manager import CompressionConfig
        config = CompressionConfig.from_env()
        assert isinstance(config, CompressionConfig)
        assert config.enabled is True

    def test_from_env_disabled(self):
        from utils.context_manager import CompressionConfig
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_ENABLED": "false"}):
            config = CompressionConfig.from_env()
            assert config.enabled is False

    def test_multiple_triggers_or_logic(self):
        from utils.context_manager import CompressionTrigger, CompressionConfig
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="tokens", value=10000),
            CompressionTrigger(type="messages", value=50),
        ])
        # tokens 满足，messages 不满足 → 应触发（OR 逻辑）
        met = any(t.is_met(12000, 10, 128000, 0.1) for t in config.triggers)
        assert met

    def test_no_triggers_met(self):
        from utils.context_manager import CompressionTrigger, CompressionConfig
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="tokens", value=10000),
            CompressionTrigger(type="messages", value=50),
        ])
        met = any(t.is_met(5000, 10, 128000, 0.04) for t in config.triggers)
        assert not met


# ============ ContextManager 测试 ============


class TestContextManager:
    """统一压缩管道测试"""

    def test_no_compression_below_threshold(self):
        from utils.context_manager import CompressionTrigger, CompressionConfig, ContextManager
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="ratio", value=0.70),
        ])
        manager = ContextManager(config=config, model_name="gpt-4o")
        messages = [{"role": "user", "content": "hello"}]
        result = manager.compress(messages=messages, search_results=[], query="test")
        assert result is None  # 不需要压缩

    def test_compression_triggered_above_threshold(self):
        from utils.context_manager import CompressionTrigger, CompressionConfig, ContextManager
        # 使用 message count 触发，更可靠
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="messages", value=3),
        ])
        manager = ContextManager(config=config, model_name="gpt-4o")
        messages = [
            {"role": "user", "content": "Write a blog about AI"},
            {"role": "tool", "content": "old tool result 1"},
            {"role": "tool", "content": "old tool result 2"},
            {"role": "tool", "content": "recent tool result"},
        ]
        result = manager.compress(messages=messages, search_results=[], query="test")
        # 应触发压缩，返回非 None
        assert result is not None

    def test_disabled_config_returns_none(self):
        from utils.context_manager import CompressionConfig, ContextManager
        config = CompressionConfig(enabled=False)
        manager = ContextManager(config=config, model_name="gpt-4o")
        messages = [{"role": "user", "content": "x" * 200000}]
        result = manager.compress(messages=messages, search_results=[], query="test")
        assert result is None

    def test_message_count_trigger(self):
        from utils.context_manager import CompressionTrigger, CompressionConfig, ContextManager
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="messages", value=5),
        ])
        manager = ContextManager(config=config, model_name="gpt-4o")
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = manager.compress(messages=messages, search_results=[], query="test")
        assert result is not None

    def test_compress_returns_metrics(self):
        """压缩结果应包含指标信息"""
        from utils.context_manager import CompressionTrigger, CompressionConfig, ContextManager
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="messages", value=3),
        ])
        manager = ContextManager(config=config, model_name="gpt-4o")
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        result = manager.compress(messages=messages, search_results=[], query="test")
        assert result is not None
        assert "_compression_layer" in result or "_messages" in result


# ============ ContextCompressionMiddleware 测试 ============


class TestContextCompressionMiddleware:
    """中间件集成测试"""

    def test_middleware_protocol(self):
        """应满足 NodeMiddleware 协议"""
        from services.blog_generator.middleware import ContextCompressionMiddleware
        mw = ContextCompressionMiddleware()
        assert hasattr(mw, 'before_node')
        assert hasattr(mw, 'after_node')

    def test_middleware_disabled_returns_none(self):
        from services.blog_generator.middleware import ContextCompressionMiddleware
        mw = ContextCompressionMiddleware()
        with patch.dict(os.environ, {"CONTEXT_COMPRESSION_ENHANCED_ENABLED": "false"}):
            result = mw.before_node({}, "writer")
            assert result is None

    def test_middleware_no_manager_returns_none(self):
        from services.blog_generator.middleware import ContextCompressionMiddleware
        mw = ContextCompressionMiddleware(context_manager=None)
        result = mw.before_node({"_messages": [], "topic": "test"}, "writer")
        assert result is None

    def test_middleware_triggers_compression(self):
        from services.blog_generator.middleware import ContextCompressionMiddleware
        from utils.context_manager import CompressionTrigger, CompressionConfig, ContextManager
        config = CompressionConfig(triggers=[
            CompressionTrigger(type="messages", value=3),
        ])
        manager = ContextManager(config=config, model_name="gpt-4o")
        mw = ContextCompressionMiddleware(context_manager=manager)
        state = {
            "_messages": [{"role": "user", "content": f"msg {i}"} for i in range(10)],
            "search_results": [],
            "topic": "test",
        }
        result = mw.before_node(state, "writer")
        assert result is not None

    def test_legacy_token_budget_still_works(self):
        """TokenBudgetMiddleware 应继续正常工作"""
        from services.blog_generator.middleware import TokenBudgetMiddleware
        mw = TokenBudgetMiddleware(total_budget=500000)
        state = {}
        result = mw.before_node(state, "writer")
        assert result is None or "_node_budget" in result
