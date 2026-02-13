"""
68.01 架构治理整合 — StyleProfile + WorkflowRegistry + safe_run 单元测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.blog_generator.style_profile import StyleProfile
from services.blog_generator.workflow_registry import WorkflowRegistry


class TestStyleProfile:
    """StyleProfile 预设和行为参数测试"""

    def test_mini_preset(self):
        s = StyleProfile.mini()
        assert s.max_revision_rounds == 1
        assert s.revision_strategy == "correct_only"
        assert s.revision_severity_filter == "high_only"
        assert s.depth_requirement == "minimal"
        assert s.enable_knowledge_refinement is False
        assert s.image_generation_mode == "mini_section"
        assert s.enable_humanizer is True
        assert s.enable_fact_check is True
        assert s.enable_thread_check is False

    def test_short_preset(self):
        s = StyleProfile.short()
        assert s.max_revision_rounds == 1
        assert s.revision_strategy == "correct_only"
        assert s.enable_humanizer is True
        assert s.enable_summary_gen is True

    def test_medium_preset(self):
        s = StyleProfile.medium()
        assert s.max_revision_rounds == 3
        assert s.revision_strategy == "full_revise"
        assert s.revision_severity_filter == "all"
        assert s.enable_knowledge_refinement is True
        assert s.enable_thread_check is True

    def test_long_preset(self):
        s = StyleProfile.long()
        assert s.max_revision_rounds == 5
        assert s.depth_requirement == "deep"
        assert s.enable_fact_check is True

    def test_deep_analysis_preset(self):
        s = StyleProfile.deep_analysis()
        assert s.tone == "academic"
        assert s.enable_fact_check is True
        assert s.max_revision_rounds == 5

    def test_science_popular_preset(self):
        s = StyleProfile.science_popular()
        assert s.tone == "casual"
        assert s.complexity == "beginner"
        assert s.image_style == "watercolor"

    def test_from_target_length_mapping(self):
        """向后兼容：target_length 映射到正确的预设"""
        for length, expected_rounds in [
            ('mini', 1), ('short', 1), ('medium', 3), ('long', 5), ('custom', 3)
        ]:
            s = StyleProfile.from_target_length(length)
            assert s.max_revision_rounds == expected_rounds, f"{length} should have {expected_rounds} rounds"

    def test_from_target_length_unknown_defaults_to_medium(self):
        s = StyleProfile.from_target_length('unknown')
        assert s.max_revision_rounds == 3

    def test_custom_override(self):
        """用户可以自定义覆盖任何参数"""
        s = StyleProfile(
            max_revision_rounds=10,
            tone="humorous",
            enable_fact_check=True,
        )
        assert s.max_revision_rounds == 10
        assert s.tone == "humorous"
        assert s.enable_fact_check is True


class TestWorkflowRegistry:
    """WorkflowRegistry 注册和获取测试"""

    def setup_method(self):
        WorkflowRegistry.clear()

    def test_register_and_get(self):
        @WorkflowRegistry.register("test", default_style=StyleProfile.mini(), description="Test")
        def create_test(style):
            return style

        result = WorkflowRegistry.get("test")
        assert isinstance(result, StyleProfile)
        assert result.max_revision_rounds == 1

    def test_get_nonexistent_raises(self):
        with pytest.raises(KeyError, match="不存在"):
            WorkflowRegistry.get("nonexistent")

    def test_user_style_overrides_default(self):
        @WorkflowRegistry.register("test2", default_style=StyleProfile.mini())
        def create_test2(style):
            return style

        custom = StyleProfile(max_revision_rounds=99)
        result = WorkflowRegistry.get("test2", style=custom)
        assert result.max_revision_rounds == 99

    def test_list_workflows(self):
        @WorkflowRegistry.register("a", description="Alpha")
        def create_a(style):
            return style

        @WorkflowRegistry.register("b", description="Beta")
        def create_b(style):
            return style

        listing = WorkflowRegistry.list_workflows()
        assert listing == {"a": "Alpha", "b": "Beta"}

    def test_get_default_style(self):
        @WorkflowRegistry.register("ds", default_style=StyleProfile.long())
        def create_ds(style):
            return style

        default = WorkflowRegistry.get_default_style("ds")
        assert default.max_revision_rounds == 5


class TestWorkflowsRegistration:
    """验证 workflows.py 注册了 6 种工作流"""

    def setup_method(self):
        WorkflowRegistry.clear()
        # 强制重新执行 workflows 模块的注册逻辑
        import importlib
        import services.blog_generator.workflows as wf_mod
        importlib.reload(wf_mod)

    def test_all_workflows_registered(self):
        # 导入 workflows 模块触发注册
        import services.blog_generator.workflows  # noqa: F401

        listing = WorkflowRegistry.list_workflows()
        expected = {'mini', 'short', 'medium', 'long', 'deep', 'science'}
        assert set(listing.keys()) == expected

    def test_each_workflow_returns_style(self):
        import services.blog_generator.workflows  # noqa: F401

        for name in ['mini', 'short', 'medium', 'long', 'deep', 'science']:
            result = WorkflowRegistry.get(name)
            assert isinstance(result, StyleProfile), f"{name} should return StyleProfile"


class TestSafeRun:
    """safe_run 装饰器测试"""

    def test_normal_execution(self):
        from utils.safe_run import safe_run

        class FakeNode:
            @safe_run(default_return={"x": 0})
            def run(self, state):
                state["x"] = 42
                return state

        node = FakeNode()
        result = node.run({"x": 0})
        assert result["x"] == 42

    def test_exception_graceful_degradation(self):
        from utils.safe_run import safe_run

        class FakeNode:
            @safe_run(default_return={"x": -1})
            def run(self, state):
                raise RuntimeError("boom")

        node = FakeNode()
        result = node.run({"x": 0})
        assert result["x"] == -1


class TestGeneratorStyleIntegration:
    """验证 generator.py 的 StyleProfile 集成"""

    @pytest.fixture(autouse=True)
    def _patch_diskcache(self, monkeypatch, tmp_path):
        """避免 diskcache 读取损坏的 sqlite 文件"""
        monkeypatch.setenv('DISKCACHE_DIR', str(tmp_path / 'cache'))

    def _make_generator(self, style=None):
        from unittest.mock import MagicMock, patch

        llm = MagicMock()
        llm.chat = MagicMock(return_value="{}")

        # Patch SearchCoordinator 和 ResearcherAgent 避免 diskcache 初始化
        with patch('services.blog_generator.generator.SearchCoordinator'), \
             patch('services.blog_generator.generator.ResearcherAgent'):
            from services.blog_generator.generator import BlogGenerator
            return BlogGenerator(llm, style=style)

    def test_get_style_from_instance(self):
        """实例级 style 优先"""
        gen = self._make_generator(style=StyleProfile.long())
        state = {'target_length': 'mini'}
        style = gen._get_style(state)
        assert style.max_revision_rounds == 5  # long, not mini

    def test_get_style_fallback_to_target_length(self):
        """无实例 style 时从 target_length 推断"""
        gen = self._make_generator()
        state = {'target_length': 'mini'}
        style = gen._get_style(state)
        assert style.max_revision_rounds == 1  # mini

    def test_is_enabled_both_true(self):
        gen = self._make_generator()
        assert gen._is_enabled(True, True) is True

    def test_is_enabled_env_false(self):
        gen = self._make_generator()
        assert gen._is_enabled(False, True) is False

    def test_is_enabled_style_false(self):
        gen = self._make_generator()
        assert gen._is_enabled(True, False) is False
