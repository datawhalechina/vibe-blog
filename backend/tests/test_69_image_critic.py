#!/usr/bin/env python3
"""
[需求点 69] AutoFigure Artist 优化 — Generator-Critic Loop 单元测试

验证：
  IC1 image_evaluator.j2 模板渲染
  IC2 image_improve.j2 模板渲染
  IC3 ArtistAgent.evaluate_image 成功路径
  IC4 ArtistAgent.evaluate_image 降级路径
  IC5 ArtistAgent.improve_image 成功路径
  IC6 ArtistAgent.improve_image 无问题时跳过
  IC7 ArtistAgent.refine_image 达到阈值停止
  IC8 ArtistAgent.refine_image 无改进停止
  IC9 ArtistAgent.refine_image 达到最大轮数停止
  IC10 generate_image 中 IMAGE_REFINE_ENABLED 开关

用法：
  cd backend
  python -m pytest tests/test_69_image_critic.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImageEvaluatorTemplate:
    def test_template_renders(self):
        """IC1: image_evaluator.j2 渲染包含关键字段"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_image_evaluator(
            code="flowchart TB\n    A[Start] --> B[End]",
            description="简单流程图",
        )
        assert "flowchart TB" in result
        assert "简单流程图" in result
        assert "structural_accuracy" in result
        assert "visual_clarity" in result


class TestImageImproveTemplate:
    def test_template_renders(self):
        """IC2: image_improve.j2 渲染包含关键字段"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_image_improve(
            original_code="flowchart TB\n    A --> B",
            scores={"structural_accuracy": 5},
            specific_issues=["节点缺少标签"],
            improvement_suggestions=["为节点添加中文标签"],
        )
        assert "flowchart TB" in result
        assert "structural_accuracy" in result
        assert "节点缺少标签" in result
        assert "为节点添加中文标签" in result


class TestEvaluateImage:
    def setup_method(self):
        self.mock_llm = MagicMock()
        from services.blog_generator.agents.artist import ArtistAgent
        self.agent = ArtistAgent(self.mock_llm)

    def test_evaluate_success(self):
        """IC3: 正常评估返回结构化结果"""
        self.mock_llm.chat.return_value = json.dumps({
            "scores": {
                "structural_accuracy": 8,
                "visual_clarity": 7,
                "content_fidelity": 9,
                "syntax_correctness": 8,
            },
            "overall_quality": 8.0,
            "specific_issues": ["布局略紧凑"],
            "improvement_suggestions": ["增加节点间距"],
        })

        result = self.agent.evaluate_image(
            code="flowchart TB\n    A --> B",
            description="测试",
        )

        assert result["overall_quality"] == 8.0
        assert result["scores"]["structural_accuracy"] == 8
        assert len(result["specific_issues"]) == 1

    def test_evaluate_failure_returns_default(self):
        """IC4: LLM 失败时返回默认分数"""
        self.mock_llm.chat.side_effect = Exception("timeout")

        result = self.agent.evaluate_image(code="flowchart TB\n    A --> B")

        assert result["overall_quality"] == 7.0
        assert result["specific_issues"] == []

    def test_evaluate_empty_response(self):
        """IC4b: 空响应返回默认分数"""
        self.mock_llm.chat.return_value = ""

        result = self.agent.evaluate_image(code="flowchart TB\n    A --> B")

        assert result["overall_quality"] == 7.0


class TestImproveImage:
    def setup_method(self):
        self.mock_llm = MagicMock()
        from services.blog_generator.agents.artist import ArtistAgent
        self.agent = ArtistAgent(self.mock_llm)

    def test_improve_success(self):
        """IC5: 正常改进返回新代码"""
        self.mock_llm.chat.return_value = "flowchart TB\n    A[开始] --> B[结束]"

        result = self.agent.improve_image(
            original_code="flowchart TB\n    A --> B",
            critique={
                "scores": {"structural_accuracy": 5},
                "specific_issues": ["缺少标签"],
                "improvement_suggestions": ["添加中文标签"],
            },
        )

        assert "开始" in result
        assert self.mock_llm.chat.called

    def test_improve_no_issues_skips(self):
        """IC6: 无问题时直接返回原代码"""
        result = self.agent.improve_image(
            original_code="flowchart TB\n    A --> B",
            critique={
                "scores": {},
                "specific_issues": [],
                "improvement_suggestions": [],
            },
        )

        assert result == "flowchart TB\n    A --> B"
        assert not self.mock_llm.chat.called


class TestRefineImage:
    def setup_method(self):
        self.mock_llm = MagicMock()
        from services.blog_generator.agents.artist import ArtistAgent
        self.agent = ArtistAgent(self.mock_llm)

    def test_refine_stops_at_threshold(self):
        """IC7: 达到质量阈值时停止"""
        # evaluate returns high score
        self.mock_llm.chat.return_value = json.dumps({
            "scores": {"structural_accuracy": 9, "visual_clarity": 9,
                       "content_fidelity": 9, "syntax_correctness": 9},
            "overall_quality": 9.0,
            "specific_issues": [],
            "improvement_suggestions": [],
        })

        result = self.agent.refine_image(
            code="flowchart TB\n    A --> B",
            quality_threshold=8.0,
            max_rounds=3,
        )

        # Should only call evaluate once (score >= threshold)
        assert self.mock_llm.chat.call_count == 1
        assert result == "flowchart TB\n    A --> B"

    def test_refine_stops_when_no_improvement(self):
        """IC8: 无改进时停止"""
        call_count = [0]

        def mock_chat(**kwargs):
            call_count[0] += 1
            msgs = kwargs.get("messages", [])
            content = msgs[0]["content"] if msgs else ""
            # evaluate calls use response_format=json_object
            if kwargs.get("response_format"):
                return json.dumps({
                    "scores": {"structural_accuracy": 5},
                    "overall_quality": 5.0,
                    "specific_issues": ["问题"],
                    "improvement_suggestions": ["建议"],
                })
            # improve returns same code
            return "flowchart TB\n    A --> B"

        self.mock_llm.chat.side_effect = lambda **kw: mock_chat(**kw)

        result = self.agent.refine_image(
            code="flowchart TB\n    A --> B",
            quality_threshold=9.0,
            max_rounds=3,
        )

        # Should stop after 1 round (evaluate + improve, but code unchanged)
        assert result == "flowchart TB\n    A --> B"

    def test_refine_max_rounds(self):
        """IC9: 达到最大轮数时停止"""
        round_counter = [0]

        def mock_chat(**kwargs):
            # evaluate calls use response_format=json_object
            if kwargs.get("response_format"):
                round_counter[0] += 1
                return json.dumps({
                    "scores": {"structural_accuracy": 5},
                    "overall_quality": 5.0,
                    "specific_issues": ["问题"],
                    "improvement_suggestions": ["建议"],
                })
            return f"flowchart TB\n    A[v{round_counter[0]}] --> B"

        self.mock_llm.chat.side_effect = lambda **kw: mock_chat(**kw)

        result = self.agent.refine_image(
            code="flowchart TB\n    A --> B",
            quality_threshold=9.0,
            max_rounds=2,
        )

        # Should have evaluated exactly 2 times
        assert round_counter[0] == 2


class TestGenerateImageRefineToggle:
    def test_refine_disabled_by_default(self):
        """IC10: IMAGE_REFINE_ENABLED 默认关闭"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    A --> B",
            "caption": "图",
        })

        from services.blog_generator.agents.artist import ArtistAgent
        agent = ArtistAgent(mock_llm)

        with patch.dict("os.environ", {"IMAGE_REFINE_ENABLED": "false"}):
            result = agent.generate_image(
                image_type="flowchart",
                description="测试",
                context="上下文",
            )

        # Only 1 LLM call (generate), no evaluate/improve
        assert mock_llm.chat.call_count == 1
        assert result["render_method"] == "mermaid"
