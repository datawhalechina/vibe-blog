#!/usr/bin/env python3
"""
[需求点 68.01] 架构治理整合 — 单元测试

验证：
  1. StyleProfile 预设套餐正确性
  2. StyleProfile.from_target_length 向后兼容
  3. WorkflowRegistry 注册与获取
  4. AgentRunner JSON 提取
  5. safe_run 优雅降级

用法：
  cd backend
  python -m pytest tests/test_68_01_governance.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.blog_generator.style_profile import StyleProfile
from services.blog_generator.workflow_registry import WorkflowRegistry
from utils.agent_runner import extract_json, AgentRunner
from utils.safe_run import safe_run


# ============================================================
# StyleProfile 预设测试
# ============================================================

class TestStyleProfilePresets:
    def test_mini_preset(self):
        s = StyleProfile.mini()
        assert s.max_revision_rounds == 1
        assert s.revision_strategy == "correct_only"
        assert s.revision_severity_filter == "high_only"
        assert s.depth_requirement == "minimal"
        assert s.enable_knowledge_refinement is False
        assert s.image_generation_mode == "mini_section"
        assert s.enable_humanizer is False
        assert s.enable_fact_check is False

    def test_short_preset(self):
        s = StyleProfile.short()
        assert s.max_revision_rounds == 1
        assert s.revision_strategy == "correct_only"
        assert s.depth_requirement == "shallow"
        assert s.enable_knowledge_refinement is False
        assert s.enable_humanizer is True

    def test_medium_preset(self):
        s = StyleProfile.medium()
        assert s.max_revision_rounds == 3
        assert s.revision_strategy == "full_revise"
        assert s.revision_severity_filter == "all"
        assert s.depth_requirement == "medium"
        assert s.enable_knowledge_refinement is True

    def test_long_preset(self):
        s = StyleProfile.long()
        assert s.max_revision_rounds == 5
        assert s.depth_requirement == "deep"
        assert s.enable_fact_check is True
        assert s.enable_thread_check is True

    def test_deep_analysis_preset(self):
        s = StyleProfile.deep_analysis()
        assert s.tone == "academic"
        assert s.enable_fact_check is True

    def test_from_target_length_mapping(self):
        """向后兼容：target_length 字符串映射到正确预设"""
        assert StyleProfile.from_target_length('mini').max_revision_rounds == 1
        assert StyleProfile.from_target_length('short').depth_requirement == "shallow"
        assert StyleProfile.from_target_length('medium').max_revision_rounds == 3
        assert StyleProfile.from_target_length('long').max_revision_rounds == 5
        assert StyleProfile.from_target_length('custom').max_revision_rounds == 3  # 默认 medium
        assert StyleProfile.from_target_length('unknown').max_revision_rounds == 3  # 兜底 medium

    def test_preset_ordering(self):
        """预设的修订轮数应递增"""
        mini = StyleProfile.mini()
        short = StyleProfile.short()
        medium = StyleProfile.medium()
        long_ = StyleProfile.long()
        assert mini.max_revision_rounds <= short.max_revision_rounds
        assert short.max_revision_rounds <= medium.max_revision_rounds
        assert medium.max_revision_rounds <= long_.max_revision_rounds


# ============================================================
# WorkflowRegistry 测试
# ============================================================

class TestWorkflowRegistry:
    def setup_method(self):
        WorkflowRegistry.clear()

    def test_register_and_get(self):
        @WorkflowRegistry.register("test_wf", description="Test workflow")
        def create_test(style):
            return {"style": style}

        result = WorkflowRegistry.get("test_wf")
        assert result["style"] is not None

    def test_get_nonexistent_raises(self):
        import pytest
        with pytest.raises(KeyError):
            WorkflowRegistry.get("nonexistent")

    def test_list_workflows(self):
        @WorkflowRegistry.register("wf_a", description="Workflow A")
        def create_a(style):
            return style

        @WorkflowRegistry.register("wf_b", description="Workflow B")
        def create_b(style):
            return style

        listing = WorkflowRegistry.list_workflows()
        assert "wf_a" in listing
        assert "wf_b" in listing
        assert listing["wf_a"] == "Workflow A"

    def test_custom_style_overrides_default(self):
        default = StyleProfile.mini()

        @WorkflowRegistry.register("override_test", default_style=default)
        def create_override(style):
            return style

        custom = StyleProfile(max_revision_rounds=99)
        result = WorkflowRegistry.get("override_test", style=custom)
        assert result.max_revision_rounds == 99

    def test_default_style_used_when_no_override(self):
        default = StyleProfile(max_revision_rounds=42)

        @WorkflowRegistry.register("default_test", default_style=default)
        def create_default(style):
            return style

        result = WorkflowRegistry.get("default_test")
        assert result.max_revision_rounds == 42


# ============================================================
# AgentRunner 测试
# ============================================================

class TestExtractJson:
    def test_plain_json(self):
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_wrapped_json(self):
        result = extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_markdown_wrapped_no_lang(self):
        result = extract_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        result = extract_json('Here is the result:\n```json\n{"score": 5}\n```\nDone.')
        assert result == {"score": 5}

    def test_invalid_json_raises(self):
        import pytest
        with pytest.raises(Exception):
            extract_json('not json at all')


class TestAgentRunner:
    def test_chat_delegates_to_llm(self):
        class MockLLM:
            def chat(self, **kwargs):
                return "hello"

        runner = AgentRunner(MockLLM())
        assert runner.chat([{"role": "user", "content": "hi"}]) == "hello"

    def test_chat_json_parses_response(self):
        class MockLLM:
            def chat(self, **kwargs):
                return '```json\n{"result": 42}\n```'

        runner = AgentRunner(MockLLM())
        result = runner.chat_json([{"role": "user", "content": "test"}])
        assert result == {"result": 42}

    def test_chat_json_retries_on_failure(self):
        call_count = 0

        class MockLLM:
            def chat(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    return "invalid json"
                return '{"ok": true}'

        runner = AgentRunner(MockLLM())
        result = runner.chat_json(
            [{"role": "user", "content": "test"}],
            max_retries=2,
        )
        assert result == {"ok": True}
        assert call_count == 2


# ============================================================
# safe_run 测试
# ============================================================

class TestSafeRun:
    def test_normal_execution(self):
        class Agent:
            @safe_run(default_return={"fallback": True})
            def run(self, state):
                state["result"] = 42
                return state

        agent = Agent()
        state = {}
        result = agent.run(state)
        assert result["result"] == 42
        assert "fallback" not in result

    def test_exception_returns_default(self):
        class Agent:
            @safe_run(default_return={"fallback": True})
            def run(self, state):
                raise RuntimeError("boom")

        agent = Agent()
        state = {"existing": "data"}
        result = agent.run(state)
        assert result["fallback"] is True
        assert result["existing"] == "data"

    def test_exception_preserves_state(self):
        class Agent:
            @safe_run(default_return={})
            def run(self, state):
                state["before_error"] = True
                raise ValueError("fail")

        agent = Agent()
        state = {"original": True}
        result = agent.run(state)
        assert result["original"] is True
        assert result["before_error"] is True
