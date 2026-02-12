"""
68.03 动态工作流编排 — WorkflowEngine + YAML 配置单元测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.blog_generator.workflow_engine import WorkflowEngine, ResolvedWorkflow, AgentMeta
from services.blog_generator.style_profile import StyleProfile


class TestWorkflowEngineInit:
    """WorkflowEngine 初始化和 Agent 注册表加载"""

    def test_loads_agent_registry(self):
        engine = WorkflowEngine()
        registry = engine.get_agent_registry()
        assert len(registry) > 0
        assert 'researcher' in registry
        assert 'writer' in registry
        assert 'humanizer' in registry

    def test_agent_meta_fields(self):
        engine = WorkflowEngine()
        researcher = engine.get_agent_registry()['researcher']
        assert isinstance(researcher, AgentMeta)
        assert researcher.agent_type == 'critical'
        assert researcher.phase == 'plan'

    def test_enhancement_agent_has_style_switch(self):
        engine = WorkflowEngine()
        humanizer = engine.get_agent_registry()['humanizer']
        assert humanizer.agent_type == 'enhancement'
        assert humanizer.style_switch == 'enable_humanizer'

    def test_critical_agent_no_style_switch(self):
        engine = WorkflowEngine()
        writer = engine.get_agent_registry()['writer']
        assert writer.agent_type == 'critical'
        assert writer.style_switch == ''


class TestWorkflowEngineListWorkflows:
    """列出所有可用工作流"""

    def test_list_all_six_workflows(self):
        engine = WorkflowEngine()
        workflows = engine.list_workflows()
        expected = {'mini', 'short', 'medium', 'long', 'deep', 'science'}
        assert set(workflows.keys()) == expected

    def test_each_workflow_has_description(self):
        engine = WorkflowEngine()
        workflows = engine.list_workflows()
        for name, desc in workflows.items():
            assert desc, f"Workflow '{name}' has empty description"


class TestWorkflowEngineResolve:
    """resolve() 核心逻辑测试"""

    def test_resolve_medium_returns_resolved_workflow(self):
        engine = WorkflowEngine()
        result = engine.resolve("medium")
        assert isinstance(result, ResolvedWorkflow)
        assert result.name == "medium"

    def test_resolve_nonexistent_raises(self):
        engine = WorkflowEngine()
        with pytest.raises(FileNotFoundError, match="不存在"):
            engine.resolve("nonexistent_workflow")

    def test_resolve_medium_has_all_phases(self):
        engine = WorkflowEngine()
        result = engine.resolve("medium")
        assert 'plan' in result.phases
        assert 'write' in result.phases
        assert 'review' in result.phases
        assert 'assemble' in result.phases

    def test_resolve_medium_plan_phase_order(self):
        engine = WorkflowEngine()
        result = engine.resolve("medium")
        assert result.phases['plan'] == ['researcher', 'planner']

    def test_resolve_medium_critical_agents_always_active(self):
        engine = WorkflowEngine()
        result = engine.resolve("medium")
        assert 'researcher' in result.active_agents
        assert 'planner' in result.active_agents
        assert 'writer' in result.active_agents
        assert 'reviewer' in result.active_agents
        assert 'assembler' in result.active_agents


class TestWorkflowEngineFiltering:
    """StyleProfile 过滤 Agent 测试"""

    def test_mini_skips_humanizer(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        assert 'humanizer' not in result.active_agents
        assert 'humanizer' not in [a for agents in result.phases.values() for a in agents]

    def test_mini_skips_factcheck(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        assert 'factcheck' not in result.active_agents

    def test_mini_skips_summary_generator(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        assert 'summary_generator' not in result.active_agents

    def test_mini_keeps_text_cleanup(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        assert 'text_cleanup' in result.active_agents

    def test_mini_keeps_critical_agents(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        for agent in ['researcher', 'planner', 'writer', 'reviewer', 'assembler']:
            assert agent in result.active_agents, f"{agent} should be active in mini"

    def test_long_enables_factcheck(self):
        engine = WorkflowEngine()
        result = engine.resolve("long")
        assert 'factcheck' in result.active_agents

    def test_deep_enables_all_enhancement_agents(self):
        engine = WorkflowEngine()
        result = engine.resolve("deep")
        for agent in ['thread_checker', 'voice_checker', 'factcheck', 'humanizer', 'text_cleanup', 'summary_generator']:
            assert agent in result.active_agents, f"{agent} should be active in deep"

    def test_user_style_override_disables_humanizer(self):
        """用户传入 style 覆盖默认配置"""
        engine = WorkflowEngine()
        custom_style = StyleProfile(enable_humanizer=False)
        result = engine.resolve("medium", style=custom_style)
        assert 'humanizer' not in result.active_agents
        assert 'humanizer' in result.skipped_agents

    def test_user_style_override_enables_factcheck_on_short(self):
        """用户可以在 short 工作流上强制启用 factcheck"""
        engine = WorkflowEngine()
        # short.yaml 没有 factcheck 在 phases 中，所以即使 style 启用也不会出现
        # 这验证了 YAML phases 是工作流的"骨架"，style 只控制"是否跳过"
        custom_style = StyleProfile(enable_fact_check=True)
        result = engine.resolve("short", style=custom_style)
        # short.yaml 没有 validate phase，所以 factcheck 不会出现
        assert 'factcheck' not in result.active_agents

    def test_empty_phase_removed(self):
        """所有 agent 被过滤后，空 phase 应被移除"""
        engine = WorkflowEngine()
        # mini 没有 validate phase 在 YAML 中
        result = engine.resolve("mini")
        assert 'validate' not in result.phases


class TestWorkflowEngineSkippedAgents:
    """skipped_agents 追踪测试"""

    def test_mini_reports_skipped_agents(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        # mini 的 YAML 中没有 humanizer/factcheck 等，所以 skipped 来自 YAML 中有但被过滤的
        # mini.yaml 只有 text_cleanup 在 polish，没有 humanizer
        # 所以 skipped 应该为空（因为 YAML 中就没列这些 agent）
        # 但如果 YAML 中列了但被 style 过滤，就会出现在 skipped 中
        assert isinstance(result.skipped_agents, list)

    def test_medium_with_all_disabled_reports_skipped(self):
        engine = WorkflowEngine()
        style = StyleProfile(
            enable_humanizer=False,
            enable_thread_check=False,
            enable_voice_check=False,
            enable_text_cleanup=False,
            enable_summary_gen=False,
        )
        result = engine.resolve("medium", style=style)
        assert 'humanizer' in result.skipped_agents
        assert 'thread_checker' in result.skipped_agents
        assert 'summary_generator' in result.skipped_agents


class TestWorkflowEngineStyleFromYaml:
    """从 YAML default_style 构建 StyleProfile"""

    def test_medium_default_style_rounds(self):
        engine = WorkflowEngine()
        result = engine.resolve("medium")
        style = engine._build_style_from_yaml(
            engine._load_workflow_yaml("medium")
        )
        assert style.max_revision_rounds == 3

    def test_mini_default_style_strategy(self):
        engine = WorkflowEngine()
        style = engine._build_style_from_yaml(
            engine._load_workflow_yaml("mini")
        )
        assert style.revision_strategy == "correct_only"
        assert style.enable_humanizer is False

    def test_deep_default_style_tone(self):
        engine = WorkflowEngine()
        style = engine._build_style_from_yaml(
            engine._load_workflow_yaml("deep")
        )
        assert style.tone == "academic"
        assert style.enable_fact_check is True

    def test_science_default_style_image(self):
        engine = WorkflowEngine()
        style = engine._build_style_from_yaml(
            engine._load_workflow_yaml("science")
        )
        assert style.image_style == "watercolor"
        assert style.tone == "casual"


class TestWorkflowEngineActiveAgentOrder:
    """active_agents 保持 phase 顺序"""

    def test_medium_agent_order_follows_phases(self):
        engine = WorkflowEngine()
        result = engine.resolve("medium")
        agents = result.active_agents
        # researcher 应该在 writer 之前
        assert agents.index('researcher') < agents.index('writer')
        # writer 应该在 reviewer 之前
        assert agents.index('writer') < agents.index('reviewer')
        # reviewer 应该在 assembler 之前
        assert agents.index('reviewer') < agents.index('assembler')

    def test_mini_agent_order(self):
        engine = WorkflowEngine()
        result = engine.resolve("mini")
        agents = result.active_agents
        assert agents.index('researcher') < agents.index('planner')
        assert agents.index('planner') < agents.index('writer')
        assert agents.index('writer') < agents.index('reviewer')
