"""
102.02 中间件管道升级 — 单元测试
测试 before_pipeline/after_pipeline/on_error 钩子、FeatureToggle、GracefulDegradation
"""

import os
import time
import pytest
from unittest.mock import patch


from services.blog_generator.middleware import (
    MiddlewarePipeline,
    ExtendedMiddleware,
    FeatureToggleMiddleware,
    GracefulDegradationMiddleware,
    TOGGLE_MAP,
    DEGRADABLE_NODES,
)


# ============================================================
# Test helpers
# ============================================================

class RecordingMiddleware(ExtendedMiddleware):
    """记录所有钩子调用的中间件"""
    def __init__(self, tag, log):
        self.tag = tag
        self.log = log

    def before_pipeline(self, state):
        self.log.append(f"{self.tag}.before_pipeline")
        return None

    def after_pipeline(self, state):
        self.log.append(f"{self.tag}.after_pipeline")
        return None

    def before_node(self, state, node_name):
        self.log.append(f"{self.tag}.before_node({node_name})")
        return None

    def after_node(self, state, node_name):
        self.log.append(f"{self.tag}.after_node({node_name})")
        return None


# ============================================================
# 1. ExtendedMiddleware 基类
# ============================================================

class TestExtendedMiddleware:
    def test_all_hooks_return_none(self):
        mw = ExtendedMiddleware()
        assert mw.before_pipeline({}) is None
        assert mw.after_pipeline({}) is None
        assert mw.before_node({}, "x") is None
        assert mw.after_node({}, "x") is None
        assert mw.on_error({}, "x", Exception()) is None


# ============================================================
# 2. MiddlewarePipeline before/after_pipeline
# ============================================================

class TestPipelineLifecycle:
    def test_before_pipeline_order(self):
        log = []
        p = MiddlewarePipeline([RecordingMiddleware("A", log), RecordingMiddleware("B", log)])
        p.run_before_pipeline({})
        assert log == ["A.before_pipeline", "B.before_pipeline"]

    def test_after_pipeline_reverse_order(self):
        log = []
        p = MiddlewarePipeline([RecordingMiddleware("A", log), RecordingMiddleware("B", log)])
        p.run_after_pipeline({})
        assert log == ["B.after_pipeline", "A.after_pipeline"]

    def test_before_pipeline_merges_state(self):
        class Injector(ExtendedMiddleware):
            def before_pipeline(self, state):
                return {"injected": True}
        p = MiddlewarePipeline([Injector()])
        state = p.run_before_pipeline({"topic": "test"})
        assert state["injected"] is True
        assert state["topic"] == "test"

    def test_pipeline_exception_isolated(self):
        class Crasher(ExtendedMiddleware):
            def before_pipeline(self, state):
                raise RuntimeError("boom")
        p = MiddlewarePipeline([Crasher()])
        state = p.run_before_pipeline({"ok": True})
        assert state["ok"] is True


# ============================================================
# 3. on_error 降级钩子
# ============================================================

class TestOnError:
    def test_on_error_recovers(self):
        class Recoverer(ExtendedMiddleware):
            def on_error(self, state, node_name, error):
                if node_name == "factcheck":
                    return {"degraded": True}
                return None
        p = MiddlewarePipeline([Recoverer()])
        wrapped = p.wrap_node("factcheck", lambda s: (_ for _ in ()).throw(RuntimeError("fail")))
        result = wrapped({"topic": "test"})
        assert result["degraded"] is True

    def test_on_error_propagates_if_unhandled(self):
        p = MiddlewarePipeline([ExtendedMiddleware()])
        wrapped = p.wrap_node("writer", lambda s: (_ for _ in ()).throw(ValueError("critical")))
        with pytest.raises(ValueError, match="critical"):
            wrapped({})

    def test_first_recovery_wins(self):
        class R1(ExtendedMiddleware):
            def on_error(self, state, node_name, error):
                return {"by": "first"}
        class R2(ExtendedMiddleware):
            def on_error(self, state, node_name, error):
                return {"by": "second"}
        p = MiddlewarePipeline([R1(), R2()])
        wrapped = p.wrap_node("x", lambda s: (_ for _ in ()).throw(RuntimeError()))
        assert wrapped({})["by"] == "first"

    def test_duration_tracked(self):
        p = MiddlewarePipeline([])
        def slow(s):
            time.sleep(0.05)
            return s
        wrapped = p.wrap_node("slow", slow)
        result = wrapped({})
        assert result.get("_last_duration_ms", 0) >= 40


# ============================================================
# 4. FeatureToggleMiddleware
# ============================================================

class TestFeatureToggle:
    def test_non_toggle_node_passes(self):
        mw = FeatureToggleMiddleware()
        assert mw.before_node({}, "writer") is None

    def test_disabled_by_env(self):
        mw = FeatureToggleMiddleware()
        with patch.dict(os.environ, {"HUMANIZER_ENABLED": "false"}):
            result = mw.before_node({}, "humanizer")
            assert result == {"_skip_node": True}

    def test_enabled_by_default(self):
        mw = FeatureToggleMiddleware()
        result = mw.before_node({}, "humanizer")
        assert result is None

    def test_disabled_by_style(self):
        class FakeStyle:
            enable_humanizer = False
        mw = FeatureToggleMiddleware(style=FakeStyle())
        result = mw.before_node({}, "humanizer")
        assert result == {"_skip_node": True}

    def test_toggle_map_covers_expected_nodes(self):
        expected = {"humanizer", "factcheck", "text_cleanup",
                    "consistency_check_thread", "consistency_check_voice",
                    "summary_generator", "section_evaluate"}
        assert set(TOGGLE_MAP.keys()) == expected

    def test_feature_toggle_disabled_globally(self):
        mw = FeatureToggleMiddleware()
        with patch.dict(os.environ, {"FEATURE_TOGGLE_ENABLED": "false", "HUMANIZER_ENABLED": "false"}):
            result = mw.before_node({}, "humanizer")
            assert result is None


# ============================================================
# 5. GracefulDegradationMiddleware
# ============================================================

class TestGracefulDegradation:
    def test_degradable_node_recovers(self):
        mw = GracefulDegradationMiddleware()
        result = mw.on_error({}, "factcheck", RuntimeError("api down"))
        assert result == {}

    def test_non_degradable_node_propagates(self):
        mw = GracefulDegradationMiddleware()
        result = mw.on_error({}, "writer", RuntimeError("critical"))
        assert result is None

    def test_degradable_nodes_have_defaults(self):
        mw = GracefulDegradationMiddleware()
        for node_name, defaults in DEGRADABLE_NODES.items():
            result = mw.on_error({}, node_name, Exception("test"))
            assert result == defaults

    def test_disabled_globally(self):
        mw = GracefulDegradationMiddleware()
        with patch.dict(os.environ, {"GRACEFUL_DEGRADATION_ENABLED": "false"}):
            result = mw.on_error({}, "factcheck", RuntimeError())
            assert result is None


# ============================================================
# 6. 完整生命周期集成
# ============================================================

class TestFullLifecycle:
    def test_full_lifecycle(self):
        log = []
        p = MiddlewarePipeline([RecordingMiddleware("MW", log)])
        state = p.run_before_pipeline({"topic": "test"})
        node = p.wrap_node("researcher", lambda s: s)
        state = node(state)
        state = p.run_after_pipeline(state)
        assert log == [
            "MW.before_pipeline",
            "MW.before_node(researcher)",
            "MW.after_node(researcher)",
            "MW.after_pipeline",
        ]

    def test_degradation_in_pipeline(self):
        p = MiddlewarePipeline([GracefulDegradationMiddleware()])
        wrapped = p.wrap_node("factcheck", lambda s: (_ for _ in ()).throw(RuntimeError("down")))
        result = wrapped({"topic": "test"})
        assert result["topic"] == "test"
