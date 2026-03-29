#!/usr/bin/env python3
"""
[需求点 69.02] code2prompt 图片增强管线 — 单元测试

验证：
  E1 _get_mermaid_type 正确提取图表类型
  E2 ENHANCEABLE_TYPES 过滤非增强类型
  E3 code2prompt 模板渲染
  E4 ImageEnhancementPipeline.enhance 成功路径
  E5 ImageEnhancementPipeline.enhance 降级路径（LLM 失败）
  E6 ImageEnhancementPipeline.enhance 降级路径（图片服务不可用）
  E7 ImageEnhancementPipeline.enhance 跳过不可增强类型
  E8 PromptManager.render_code2prompt 方法存在

用法：
  cd backend
  python -m pytest tests/test_69_02_code2prompt.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.blog_generator.image_enhancement import (
    ImageEnhancementPipeline,
    _get_mermaid_type,
    ENHANCEABLE_TYPES,
)


# ========== E1: _get_mermaid_type ==========

class TestGetMermaidType:
    def test_flowchart_tb(self):
        assert _get_mermaid_type("flowchart TB\n    A --> B") == "flowchart"

    def test_graph_lr(self):
        assert _get_mermaid_type("graph LR\n    A --> B") == "graph"

    def test_class_diagram(self):
        assert _get_mermaid_type("classDiagram\n    Animal <|-- Dog") == "classDiagram"

    def test_sequence_diagram_not_enhanceable(self):
        # sequenceDiagram 不在 ENHANCEABLE_TYPES 中
        assert _get_mermaid_type("sequenceDiagram\n    A->>B: msg") == ""

    def test_empty_code(self):
        assert _get_mermaid_type("") == ""

    def test_gantt_not_enhanceable(self):
        assert _get_mermaid_type("gantt\n    title Plan") == ""


# ========== E2: ENHANCEABLE_TYPES ==========

class TestEnhanceableTypes:
    def test_flowchart_in_set(self):
        assert "flowchart" in ENHANCEABLE_TYPES

    def test_sequence_not_in_set(self):
        assert "sequenceDiagram" not in ENHANCEABLE_TYPES

    def test_mindmap_in_set(self):
        assert "mindmap" in ENHANCEABLE_TYPES


# ========== E3: code2prompt 模板渲染 ==========

class TestCode2PromptTemplate:
    def test_render_code2prompt_exists(self):
        """PromptManager 应有 render_code2prompt 方法"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        assert hasattr(pm, 'render_code2prompt')

    def test_render_code2prompt_output(self):
        """渲染结果应包含代码和风格关键词"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_code2prompt(
            code="flowchart TB\n    A --> B",
            render_method="mermaid",
            caption="测试流程图",
            style="扁平化信息图",
        )
        assert "flowchart TB" in result
        assert "扁平化信息图" in result
        assert "文字保留" in result


# ========== E4-E7: ImageEnhancementPipeline ==========

class TestImageEnhancementPipeline:
    def setup_method(self):
        self.mock_llm = MagicMock()
        self.pipeline = ImageEnhancementPipeline(self.mock_llm)

    def test_enhance_success(self):
        """E4: 完整增强流程成功"""
        # Step 1: code2prompt LLM 返回详细描述
        self.mock_llm.chat.return_value = "一张专业的流程图，从上到下展示 A 到 B 的流向。" + "x" * 100

        # Step 2: mock 图片服务
        mock_result = MagicMock()
        mock_result.oss_url = "https://oss.example.com/enhanced.png"
        mock_result.local_path = "/tmp/enhanced.png"

        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.generate.return_value = mock_result

        with patch("services.blog_generator.image_enhancement.get_image_service", return_value=mock_service):
            result = self.pipeline.enhance(
                code="flowchart TB\n    A --> B",
                render_method="mermaid",
                caption="测试",
            )

        assert result == "https://oss.example.com/enhanced.png"
        assert self.mock_llm.chat.called

    def test_enhance_llm_failure_returns_none(self):
        """E5: LLM 调用失败时降级返回 None"""
        self.mock_llm.chat.side_effect = Exception("LLM timeout")

        result = self.pipeline.enhance(
            code="flowchart TB\n    A --> B",
            render_method="mermaid",
            caption="测试",
        )
        assert result is None

    def test_enhance_image_service_unavailable(self):
        """E6: 图片服务不可用时降级返回 None"""
        self.mock_llm.chat.return_value = "详细描述" + "x" * 100

        mock_service = MagicMock()
        mock_service.is_available.return_value = False

        with patch("services.blog_generator.image_enhancement.get_image_service", return_value=mock_service):
            result = self.pipeline.enhance(
                code="flowchart TB\n    A --> B",
                render_method="mermaid",
                caption="测试",
            )
        assert result is None

    def test_enhance_skips_non_enhanceable_type(self):
        """E7: 不可增强的图表类型直接跳过"""
        result = self.pipeline.enhance(
            code="sequenceDiagram\n    A->>B: msg",
            render_method="mermaid",
            caption="测试",
        )
        assert result is None
        # LLM 不应被调用
        assert not self.mock_llm.chat.called

    def test_enhance_short_llm_response_returns_none(self):
        """LLM 返回内容过短时跳过增强"""
        self.mock_llm.chat.return_value = "太短了"

        result = self.pipeline.enhance(
            code="flowchart TB\n    A --> B",
            render_method="mermaid",
            caption="测试",
        )
        assert result is None
