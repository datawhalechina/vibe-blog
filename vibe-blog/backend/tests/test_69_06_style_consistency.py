#!/usr/bin/env python3
"""
[需求点 69.06] 参考图引导风格一致性 — 单元测试

验证：
  SA1 ArtistAgent 有 style_anchor 属性
  SA2 render_artist 接受 style_anchor 和 is_first_image 参数
  SA3 artist.j2 渲染包含风格一致性段落（有 style_anchor 时）
  SA4 artist.j2 渲染包含额外要求（is_first_image 时）
  SA5 generate_image 第一张图提取 style_description
  SA6 generate_image 后续图注入 style_anchor

用法：
  cd backend
  python -m pytest tests/test_69_06_style_consistency.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== SA1: ArtistAgent 属性 ==========

class TestArtistStyleAnchor:
    def test_artist_has_style_anchor(self):
        """SA1: ArtistAgent 初始化时有 style_anchor=None"""
        from services.blog_generator.agents.artist import ArtistAgent
        mock_llm = MagicMock()
        agent = ArtistAgent(mock_llm)
        assert agent.style_anchor is None


# ========== SA2: render_artist 参数 ==========

class TestRenderArtistParams:
    def test_render_artist_accepts_style_params(self):
        """SA2: render_artist 接受 style_anchor 和 is_first_image"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_artist(
            image_type="flowchart",
            description="测试流程图",
            context="上下文",
            style_anchor="蓝色系扁平风格",
            is_first_image=False,
        )
        assert "蓝色系扁平风格" in result
        assert "风格一致性要求" in result


# ========== SA3-SA4: 模板渲染 ==========

class TestArtistTemplateRendering:
    def test_style_anchor_in_template(self):
        """SA3: 有 style_anchor 时渲染风格一致性段落"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_artist(
            image_type="flowchart",
            description="测试",
            context="上下文",
            style_anchor="蓝色主色调，圆角矩形节点",
        )
        assert "风格一致性要求" in result
        assert "蓝色主色调" in result
        assert "配色方案完全一致" in result

    def test_no_style_anchor_no_section(self):
        """SA3b: 无 style_anchor 时不渲染风格一致性段落"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_artist(
            image_type="flowchart",
            description="测试",
            context="上下文",
        )
        assert "风格一致性要求" not in result

    def test_first_image_extra_requirement(self):
        """SA4: is_first_image 时渲染额外要求"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_artist(
            image_type="flowchart",
            description="测试",
            context="上下文",
            is_first_image=True,
        )
        assert "style_description" in result


# ========== SA5-SA6: generate_image 风格提取/注入 ==========

class TestGenerateImageStyleFlow:
    def test_first_image_extracts_style(self):
        """SA5: 第一张图从响应中提取 style_description"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    A --> B",
            "caption": "测试",
            "style_description": "蓝色系扁平风格，圆角矩形节点，灰色连线",
        })

        from services.blog_generator.agents.artist import ArtistAgent
        agent = ArtistAgent(mock_llm)
        assert agent.style_anchor is None

        agent.generate_image(
            image_type="flowchart",
            description="测试流程图",
            context="上下文",
        )

        assert agent.style_anchor == "蓝色系扁平风格，圆角矩形节点，灰色连线"

    def test_subsequent_image_uses_anchor(self):
        """SA6: 后续图的 prompt 中包含 style_anchor"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    C --> D",
            "caption": "测试",
        })

        from services.blog_generator.agents.artist import ArtistAgent
        agent = ArtistAgent(mock_llm)
        agent.style_anchor = "蓝色系扁平风格"

        agent.generate_image(
            image_type="flowchart",
            description="第二张图",
            context="上下文",
        )

        # 检查 LLM 调用的 prompt 中包含风格锚点
        call_args = mock_llm.chat.call_args
        prompt_content = call_args[1]["messages"][0]["content"]
        assert "蓝色系扁平风格" in prompt_content

    def test_first_image_no_style_desc_keeps_none(self):
        """SA5b: 第一张图如果 LLM 没返回 style_description，anchor 保持 None"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    A --> B",
            "caption": "测试",
        })

        from services.blog_generator.agents.artist import ArtistAgent
        agent = ArtistAgent(mock_llm)
        agent.generate_image(
            image_type="flowchart",
            description="测试",
            context="上下文",
        )

        assert agent.style_anchor is None
