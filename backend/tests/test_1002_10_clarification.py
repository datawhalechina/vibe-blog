"""ClarificationAgent 单元测试（1002.10 主动澄清机制）"""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _make_state(**overrides):
    """构造测试用 state"""
    base = {
        "topic": "Python 3.12 新特性 TypeVar 详解与实战",
        "article_type": "tutorial",
        "target_audience": "intermediate",
        "target_length": "medium",
        "source_material": None,
    }
    base.update(overrides)
    return base


class TestClarificationAgent:
    """测试主动澄清 Agent"""

    def setup_method(self):
        from services.blog_generator.agents.clarification import ClarificationAgent
        self.mock_llm = MagicMock()
        self.agent = ClarificationAgent(self.mock_llm)

    # --- 核心逻辑 ---

    def test_clear_topic_no_clarification(self):
        """明确主题不需要澄清"""
        self.mock_llm.chat.return_value = '{"needs_clarification": false, "questions": []}'
        result = self.agent.analyze(_make_state())
        assert result["clarification_needed"] is False
        assert result["clarification_questions"] == []

    def test_vague_topic_needs_clarification(self):
        """模糊主题需要澄清"""
        self.mock_llm.chat.return_value = json.dumps({
            "needs_clarification": True,
            "questions": [{
                "question": "您希望聚焦 AI 的哪个方向？",
                "clarification_type": "ambiguous_requirement",
                "context": "AI 涵盖范围很广",
                "options": ["大语言模型", "计算机视觉", "强化学习"],
            }],
        })
        result = self.agent.analyze(_make_state(topic="AI"))
        assert result["clarification_needed"] is True
        assert len(result["clarification_questions"]) == 1
        q = result["clarification_questions"][0]
        assert q["clarification_type"] == "ambiguous_requirement"
        assert "options" in q
    def test_max_two_questions(self):
        """最多返回 2 个澄清问题"""
        self.mock_llm.chat.return_value = json.dumps({
            "needs_clarification": True,
            "questions": [
                {"question": "q1", "clarification_type": "missing_info"},
                {"question": "q2", "clarification_type": "missing_info"},
                {"question": "q3", "clarification_type": "missing_info"},
            ],
        })
        result = self.agent.analyze(_make_state(topic="技术"))
        assert len(result["clarification_questions"]) <= 2

    def test_long_article_risk_confirmation(self):
        """长文生成触发风险确认"""
        self.mock_llm.chat.return_value = json.dumps({
            "needs_clarification": True,
            "questions": [{
                "question": "长文生成预计耗时较长，确认继续？",
                "clarification_type": "risk_confirmation",
                "context": "deep 模式资源消耗较大",
            }],
        })
        result = self.agent.analyze(_make_state(
            topic="微服务架构全景", target_length="deep",
        ))
        assert result["clarification_needed"] is True
        assert result["clarification_questions"][0]["clarification_type"] == "risk_confirmation"

    def test_all_five_clarification_types(self):
        """验证 5 种澄清类型均被接受"""
        from services.blog_generator.agents.clarification import CLARIFICATION_TYPES
        assert len(CLARIFICATION_TYPES) == 5
        assert "missing_info" in CLARIFICATION_TYPES
        assert "ambiguous_requirement" in CLARIFICATION_TYPES
        assert "approach_choice" in CLARIFICATION_TYPES
        assert "risk_confirmation" in CLARIFICATION_TYPES
        assert "suggestion" in CLARIFICATION_TYPES

    # --- 容错 ---

    def test_llm_failure_graceful_skip(self):
        """LLM 调用失败时优雅跳过"""
        self.mock_llm.chat.side_effect = Exception("API Error")
        result = self.agent.analyze(_make_state(topic="AI"))
        assert result["clarification_needed"] is False
        assert result["clarification_questions"] == []

    def test_invalid_json_graceful_skip(self):
        """LLM 返回非法 JSON 时优雅跳过"""
        self.mock_llm.chat.return_value = "not valid json"
        result = self.agent.analyze(_make_state(topic="AI"))
        assert result["clarification_needed"] is False

    def test_empty_response_graceful_skip(self):
        """LLM 返回空字符串时优雅跳过"""
        self.mock_llm.chat.return_value = ""
        result = self.agent.analyze(_make_state(topic="AI"))
        assert result["clarification_needed"] is False

    def test_invalid_clarification_type_fallback(self):
        """无效的 clarification_type 回退到 missing_info"""
        self.mock_llm.chat.return_value = json.dumps({
            "needs_clarification": True,
            "questions": [{"question": "q1", "clarification_type": "invalid_type"}],
        })
        result = self.agent.analyze(_make_state(topic="X"))
        assert result["clarification_questions"][0]["clarification_type"] == "missing_info"

    # --- 环境变量开关 ---

    def test_disabled_via_env(self):
        """环境变量 CLARIFICATION_ENABLED=false 时跳过"""
        with patch.dict(os.environ, {"CLARIFICATION_ENABLED": "false"}):
            result = self.agent.analyze(_make_state(topic="AI"))
        assert result["clarification_needed"] is False
        self.mock_llm.chat.assert_not_called()

    # --- 澄清轮数限制 ---

    def test_max_clarification_rounds(self):
        """超过最大澄清轮数时跳过"""
        self.mock_llm.chat.return_value = json.dumps({
            "needs_clarification": True,
            "questions": [{"question": "q1", "clarification_type": "missing_info"}],
        })
        result = self.agent.analyze(_make_state(
            topic="AI", clarification_round=2,
        ))
        assert result["clarification_needed"] is False
        self.mock_llm.chat.assert_not_called()


class TestClarificationFormatMessage:
    """测试澄清消息格式化"""

    def test_format_with_options(self):
        """带选项的澄清消息格式化"""
        from services.blog_generator.agents.clarification import format_clarification_message
        msg = format_clarification_message(
            question="选择方向？",
            clarification_type="approach_choice",
            options=["A", "B", "C"],
        )
        assert "🔀" in msg
        assert "选择方向？" in msg
        assert "1. A" in msg
        assert "2. B" in msg

    def test_format_without_options(self):
        """无选项的澄清消息格式化"""
        from services.blog_generator.agents.clarification import format_clarification_message
        msg = format_clarification_message(
            question="请补充信息",
            clarification_type="missing_info",
        )
        assert "❓" in msg
        assert "请补充信息" in msg

    def test_format_all_types_have_icons(self):
        """所有类型都有对应图标"""
        from services.blog_generator.agents.clarification import (
            format_clarification_message, CLARIFICATION_TYPES,
        )
        for ct in CLARIFICATION_TYPES:
            msg = format_clarification_message(
                question="test", clarification_type=ct,
            )
            assert len(msg) > 0
