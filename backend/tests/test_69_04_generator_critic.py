#!/usr/bin/env python3
"""
[需求点 69.04] 双Agent迭代优化 — 单元测试

验证：
  GC1 section_evaluator.j2 模板渲染
  GC2 writer_improve.j2 模板渲染
  GC3 QuestionerAgent.evaluate_section 成功路径
  GC4 QuestionerAgent.evaluate_section 降级路径
  GC5 WriterAgent.improve_section 成功路径
  GC6 WriterAgent.improve_section 无问题时跳过
  GC7 _should_improve_sections 逻辑
  GC8 state.py 新增字段

用法：
  cd backend
  python -m pytest tests/test_69_04_generator_critic.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== GC1-GC2: 模板渲染 ==========

class TestTemplateRendering:
    def test_section_evaluator_template(self):
        """GC1: section_evaluator.j2 渲染包含关键字段"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_section_evaluator(
            section_content="微服务架构是一种分布式系统设计方法...",
            section_title="微服务架构概述",
            prev_summary="引言",
            next_preview="核心组件",
        )
        assert "微服务架构概述" in result
        assert "信息密度" in result
        assert "逻辑连贯" in result
        assert "专业深度" in result
        assert "表达质量" in result
        assert "引言" in result
        assert "核心组件" in result

    def test_writer_improve_template(self):
        """GC2: writer_improve.j2 渲染包含关键字段"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_writer_improve(
            original_content="原始内容...",
            scores={"information_density": 5, "logical_coherence": 6},
            specific_issues=["缺少具体案例"],
            improvement_suggestions=["补充 Consul 和 Eureka 的对比"],
        )
        assert "原始内容" in result
        assert "information_density" in result
        assert "缺少具体案例" in result
        assert "补充 Consul" in result


# ========== GC3-GC4: QuestionerAgent.evaluate_section ==========

class TestEvaluateSection:
    def setup_method(self):
        self.mock_llm = MagicMock()
        from services.blog_generator.agents.questioner import QuestionerAgent
        self.agent = QuestionerAgent(self.mock_llm)

    def test_evaluate_section_success(self):
        """GC3: 正常评估返回结构化结果"""
        self.mock_llm.chat.return_value = json.dumps({
            "scores": {
                "information_density": 6,
                "logical_coherence": 7,
                "professional_depth": 5,
                "expression_quality": 8,
            },
            "overall_quality": 6.5,
            "specific_issues": ["缺少案例"],
            "improvement_suggestions": ["补充实际项目案例"],
        })

        result = self.agent.evaluate_section(
            section_content="微服务架构...",
            section_title="概述",
        )

        assert result["overall_quality"] == 6.5
        assert result["scores"]["information_density"] == 6
        assert len(result["specific_issues"]) == 1
        assert len(result["improvement_suggestions"]) == 1

    def test_evaluate_section_llm_failure(self):
        """GC4: LLM 失败时返回默认分数"""
        self.mock_llm.chat.side_effect = Exception("timeout")

        result = self.agent.evaluate_section(
            section_content="内容...",
            section_title="标题",
        )

        assert result["overall_quality"] == 7.0
        assert result["specific_issues"] == []

    def test_evaluate_section_empty_response(self):
        """GC4b: 空响应返回默认分数"""
        self.mock_llm.chat.return_value = ""

        result = self.agent.evaluate_section(
            section_content="内容...",
        )

        assert result["overall_quality"] == 7.0

    def test_evaluate_section_calculates_overall(self):
        """GC3b: 如果 LLM 没返回 overall_quality，自动计算"""
        self.mock_llm.chat.return_value = json.dumps({
            "scores": {
                "information_density": 6,
                "logical_coherence": 8,
                "professional_depth": 4,
                "expression_quality": 6,
            },
            "specific_issues": [],
            "improvement_suggestions": [],
        })

        result = self.agent.evaluate_section(section_content="内容...")
        assert result["overall_quality"] == 6.0  # (6+8+4+6)/4


# ========== GC5-GC6: WriterAgent.improve_section ==========

class TestImproveSection:
    def setup_method(self):
        self.mock_llm = MagicMock()
        from services.blog_generator.agents.writer import WriterAgent
        self.agent = WriterAgent(self.mock_llm)

    def test_improve_section_success(self):
        """GC5: 正常修改返回改进后内容"""
        self.mock_llm.chat.return_value = "改进后的内容，补充了 Consul 和 Eureka 的对比..."

        result = self.agent.improve_section(
            original_content="原始内容...",
            critique={
                "scores": {"information_density": 5},
                "specific_issues": ["缺少案例"],
                "improvement_suggestions": ["补充对比"],
            },
        )

        assert "改进后" in result
        assert self.mock_llm.chat.called

    def test_improve_section_no_issues_skips(self):
        """GC6: 无问题时直接返回原文"""
        result = self.agent.improve_section(
            original_content="原始内容...",
            critique={
                "scores": {},
                "specific_issues": [],
                "improvement_suggestions": [],
            },
        )

        assert result == "原始内容..."
        assert not self.mock_llm.chat.called

    def test_improve_section_llm_failure(self):
        """GC5b: LLM 失败时返回原文"""
        self.mock_llm.chat.side_effect = Exception("timeout")

        result = self.agent.improve_section(
            original_content="原始内容...",
            critique={
                "scores": {},
                "specific_issues": ["问题"],
                "improvement_suggestions": ["建议"],
            },
        )

        assert result == "原始内容..."


# ========== GC7: _should_improve_sections 逻辑 ==========

class TestShouldImproveSections:
    def test_no_improvement_needed(self):
        """GC7a: 所有段落达标时跳过"""
        from services.blog_generator.generator import BlogGenerator
        gen = BlogGenerator.__new__(BlogGenerator)
        state = {"needs_section_improvement": False}
        assert gen._should_improve_sections(state) == "continue"

    def test_max_rounds_reached(self):
        """GC7b: 达到最大轮数时跳过"""
        from services.blog_generator.generator import BlogGenerator
        gen = BlogGenerator.__new__(BlogGenerator)
        state = {
            "needs_section_improvement": True,
            "section_improve_count": 2,
        }
        assert gen._should_improve_sections(state) == "continue"

    def test_convergence_detected(self):
        """GC7c: 改进幅度太小时跳过"""
        from services.blog_generator.generator import BlogGenerator
        gen = BlogGenerator.__new__(BlogGenerator)
        state = {
            "needs_section_improvement": True,
            "section_improve_count": 1,
            "prev_section_avg_score": 6.5,
            "section_evaluations": [
                {"overall_quality": 6.6},
                {"overall_quality": 6.7},
            ],
        }
        assert gen._should_improve_sections(state) == "continue"

    def test_improvement_needed(self):
        """GC7d: 需要改进时返回 improve"""
        from services.blog_generator.generator import BlogGenerator
        gen = BlogGenerator.__new__(BlogGenerator)
        state = {
            "needs_section_improvement": True,
            "section_improve_count": 0,
            "prev_section_avg_score": 0,
            "section_evaluations": [
                {"overall_quality": 5.0},
                {"overall_quality": 6.0},
            ],
        }
        result = gen._should_improve_sections(state)
        assert result == "improve"


# ========== GC8: state.py 新增字段 ==========

class TestStateFields:
    def test_new_fields_in_state(self):
        """GC8: SharedState 包含新增字段"""
        from services.blog_generator.schemas.state import SharedState
        annotations = SharedState.__annotations__
        assert "section_evaluations" in annotations
        assert "needs_section_improvement" in annotations
        assert "section_improve_count" in annotations
        assert "prev_section_avg_score" in annotations

    def test_create_initial_state_defaults(self):
        """GC8b: create_initial_state 包含新字段默认值"""
        from services.blog_generator.schemas.state import create_initial_state
        state = create_initial_state(topic="test", target_length="medium")
        assert state["section_evaluations"] == []
        assert state["needs_section_improvement"] is False
        assert state["section_improve_count"] == 0
        assert state["prev_section_avg_score"] == 0.0
