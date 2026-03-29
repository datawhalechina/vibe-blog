"""
TDD 测试：特性 A — 中间件管道引擎 + 特性 E — 分布式追踪
基于 102.10.1 细化实现方案，测试先于实现编写。
所有函数签名基于 VibeBlog 真实代码扫描。
"""
import pytest
from unittest.mock import MagicMock, patch


# ==================== 特性 A：MiddlewarePipeline ====================

class TestNodeMiddlewareProtocol:
    """NodeMiddleware 协议测试"""

    def test_middleware_has_before_node(self):
        """中间件必须实现 before_node 方法"""
        from services.blog_generator.middleware import NodeMiddleware
        # Protocol 检查：实现了 before_node 的类应被视为 NodeMiddleware
        class ValidMiddleware:
            def before_node(self, state, node_name):
                return None
            def after_node(self, state, node_name):
                return None

        mw = ValidMiddleware()
        assert hasattr(mw, "before_node")
        assert hasattr(mw, "after_node")

    def test_middleware_wrap_tool_call_optional(self):
        """wrap_tool_call 是可选方法"""
        from services.blog_generator.middleware import NodeMiddleware

        class MinimalMiddleware:
            def before_node(self, state, node_name):
                return None
            def after_node(self, state, node_name):
                return None

        mw = MinimalMiddleware()
        # 不实现 wrap_tool_call 也应该可以正常工作
        assert not hasattr(mw, "wrap_tool_call") or callable(getattr(mw, "wrap_tool_call", None))


class TestMiddlewarePipeline:
    """MiddlewarePipeline 核心功能测试"""

    def test_wrap_node_returns_callable(self):
        """wrap_node 返回可调用对象"""
        from services.blog_generator.middleware import MiddlewarePipeline

        pipeline = MiddlewarePipeline()
        original_fn = lambda state: state
        wrapped = pipeline.wrap_node("test_node", original_fn)
        assert callable(wrapped)

    def test_wrap_node_executes_original(self):
        """包装后的节点执行原始函数"""
        from services.blog_generator.middleware import MiddlewarePipeline

        pipeline = MiddlewarePipeline()
        called = []
        def original(state):
            called.append(True)
            return {**state, "processed": True}

        wrapped = pipeline.wrap_node("test", original)
        result = wrapped({"topic": "test"})
        assert called == [True]
        assert result["processed"] is True

    def test_before_hook_modifies_state(self):
        """before_node 钩子可以修改传入 state"""
        from services.blog_generator.middleware import MiddlewarePipeline

        class InjectMiddleware:
            def before_node(self, state, node_name):
                return {"injected": True}
            def after_node(self, state, node_name):
                return None

        pipeline = MiddlewarePipeline(middlewares=[InjectMiddleware()])
        received_state = {}

        def capture_node(state):
            received_state.update(state)
            return state

        wrapped = pipeline.wrap_node("test", capture_node)
        wrapped({"topic": "hello"})
        assert received_state.get("injected") is True

    def test_after_hook_modifies_result(self):
        """after_node 钩子可以修改返回结果"""
        from services.blog_generator.middleware import MiddlewarePipeline

        class AppendMiddleware:
            def before_node(self, state, node_name):
                return None
            def after_node(self, state, node_name):
                return {"extra_field": "added_by_middleware"}

        pipeline = MiddlewarePipeline(middlewares=[AppendMiddleware()])
        wrapped = pipeline.wrap_node("test", lambda s: s)
        result = wrapped({"topic": "hello"})
        assert result["extra_field"] == "added_by_middleware"

    def test_middleware_chain_order(self):
        """多个中间件按注册顺序执行"""
        from services.blog_generator.middleware import MiddlewarePipeline

        order = []

        class MW1:
            def before_node(self, state, node_name):
                order.append("mw1_before")
                return None
            def after_node(self, state, node_name):
                order.append("mw1_after")
                return None

        class MW2:
            def before_node(self, state, node_name):
                order.append("mw2_before")
                return None
            def after_node(self, state, node_name):
                order.append("mw2_after")
                return None

        pipeline = MiddlewarePipeline(middlewares=[MW1(), MW2()])
        wrapped = pipeline.wrap_node("test", lambda s: s)
        wrapped({})
        assert order == ["mw1_before", "mw2_before", "mw1_after", "mw2_after"]

    def test_node_name_passed_to_middleware(self):
        """节点名称正确传递给中间件"""
        from services.blog_generator.middleware import MiddlewarePipeline

        received_names = []

        class NameCapture:
            def before_node(self, state, node_name):
                received_names.append(node_name)
                return None
            def after_node(self, state, node_name):
                return None

        pipeline = MiddlewarePipeline(middlewares=[NameCapture()])
        wrapped = pipeline.wrap_node("researcher", lambda s: s)
        wrapped({})
        assert received_names == ["researcher"]

    def test_pipeline_disabled_via_env(self):
        """MIDDLEWARE_PIPELINE_ENABLED=false 时直接执行原始函数"""
        from services.blog_generator.middleware import MiddlewarePipeline

        class ShouldNotRun:
            def before_node(self, state, node_name):
                raise RuntimeError("Should not be called")
            def after_node(self, state, node_name):
                raise RuntimeError("Should not be called")

        with patch.dict("os.environ", {"MIDDLEWARE_PIPELINE_ENABLED": "false"}):
            pipeline = MiddlewarePipeline(middlewares=[ShouldNotRun()])
            wrapped = pipeline.wrap_node("test", lambda s: {**s, "ok": True})
            result = wrapped({"topic": "test"})
            assert result["ok"] is True


# ==================== 特性 E：TracingMiddleware ====================

class TestTracingMiddleware:
    """分布式追踪中间件测试 — 复用现有 task_id_context"""

    def test_tracing_sets_context_var(self):
        """TracingMiddleware 在 before_node 中设置 ContextVar"""
        from services.blog_generator.middleware import TracingMiddleware
        from logging_config import task_id_context

        mw = TracingMiddleware()
        state = {"trace_id": "abc12345", "topic": "test"}
        mw.before_node(state, "researcher")
        assert task_id_context.get() == "abc12345"

    def test_tracing_without_trace_id(self):
        """无 trace_id 时不报错"""
        from services.blog_generator.middleware import TracingMiddleware

        mw = TracingMiddleware()
        state = {"topic": "test"}
        result = mw.before_node(state, "researcher")
        # 不应抛出异常
        assert result is None

    def test_tracing_disabled_via_env(self):
        """TRACING_ENABLED=false 时跳过"""
        from services.blog_generator.middleware import TracingMiddleware

        with patch.dict("os.environ", {"TRACING_ENABLED": "false"}):
            mw = TracingMiddleware()
            state = {"trace_id": "abc12345"}
            result = mw.before_node(state, "researcher")
            assert result is None
