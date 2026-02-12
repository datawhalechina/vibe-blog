#!/usr/bin/env python3
"""
[需求点 69.06] 参考图引导风格一致性 — 单元测试

验证：
  SA1 ArtistAgent 初始化 style_anchor 为 None
  SA2 generate_image 第一张图 is_first_image=True
  SA3 generate_image 第一张图提取 style_description 设为 style_anchor
  SA4 generate_image 后续图 is_first_image=False 且注入 style_anchor
  SA5 generate_image LLM 未返回 style_description 时 style_anchor 保持 None
  SA6 artist.j2 模板包含 style_anchor 条件块
  SA7 artist.j2 模板包含 is_first_image 条件块
  SA8 prompt_manager.render_artist 接受 style_anchor 和 is_first_image 参数

用法：
  cd backend
  python -m pytest tests/test_69_06_style_anchor.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestStyleAnchorInit:
    def test_style_anchor_none_on_init(self):
        """SA1: ArtistAgent 初始化时 style_anchor 为 None"""
        from services.blog_generator.agents.artist import ArtistAgent
        agent = ArtistAgent(MagicMock())
        assert agent.style_anchor is None


class TestStyleAnchorExtraction:
    def setup_method(self):
        self.mock_llm = MagicMock()
        from services.blog_generator.agents.artist import ArtistAgent
        self.agent = ArtistAgent(self.mock_llm)

    def test_first_image_sets_style_anchor(self):
        """SA3: 第一张图的 style_description 被提取为 style_anchor"""
        self.mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    A[Start] --> B[End]",
            "caption": "测试图",
            "style_description": "蓝色系扁平风格，圆角矩形节点，灰色连线"
        })

        result = self.agent.generate_image(
            image_type="flowchart",
            description="测试流程图",
            context="测试上下文",
        )

        assert self.agent.style_anchor == "蓝色系扁平风格，圆角矩形节点，灰色连线"
        assert result["render_method"] == "mermaid"

    def test_subsequent_image_uses_style_anchor(self):
        """SA4: 后续图使用已有的 style_anchor"""
        # 先设定 style_anchor
        self.agent.style_anchor = "蓝色系扁平风格"

        self.mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    C[Step1] --> D[Step2]",
            "caption": "第二张图",
        })

        self.agent.generate_image(
            image_type="flowchart",
            description="第二张流程图",
            context="第二章上下文",
        )

        # 验证 prompt 中包含 style_anchor
        call_args = self.mock_llm.chat.call_args
        prompt_content = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0][0]["content"]
        assert "蓝色系扁平风格" in prompt_content

    def test_no_style_description_keeps_none(self):
        """SA5: LLM 未返回 style_description 时 style_anchor 保持 None"""
        self.mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    A --> B",
            "caption": "图",
        })

        self.agent.generate_image(
            image_type="flowchart",
            description="测试",
            context="上下文",
        )

        assert self.agent.style_anchor is None

    def test_is_first_image_flag(self):
        """SA2: 第一张图 is_first_image=True，后续为 False"""
        # 第一次调用
        self.mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    A --> B",
            "caption": "图",
            "style_description": "蓝色扁平风格"
        })

        self.agent.generate_image(
            image_type="flowchart",
            description="第一张",
            context="上下文",
        )

        # 第一次调用的 prompt 应包含 style_description 要求
        first_prompt = self.mock_llm.chat.call_args[1]["messages"][0]["content"] if "messages" in self.mock_llm.chat.call_args[1] else self.mock_llm.chat.call_args[0][0][0]["content"]
        assert "style_description" in first_prompt

        # 第二次调用
        self.mock_llm.chat.return_value = json.dumps({
            "render_method": "mermaid",
            "content": "flowchart TB\n    C --> D",
            "caption": "图2",
        })

        self.agent.generate_image(
            image_type="flowchart",
            description="第二张",
            context="上下文2",
        )

        # 第二次调用的 prompt 应包含风格一致性要求
        second_prompt = self.mock_llm.chat.call_args[1]["messages"][0]["content"] if "messages" in self.mock_llm.chat.call_args[1] else self.mock_llm.chat.call_args[0][0][0]["content"]
        assert "蓝色扁平风格" in second_prompt


class TestTemplateIntegration:
    def test_artist_template_has_style_anchor_block(self):
        """SA6: artist.j2 包含 style_anchor 条件块"""
        template_path = Path(__file__).parent.parent / "infrastructure" / "prompts" / "blog" / "artist.j2"
        content = template_path.read_text()
        assert "{% if style_anchor %}" in content
        assert "风格一致性要求" in content

    def test_artist_template_has_first_image_block(self):
        """SA7: artist.j2 包含 is_first_image 条件块"""
        template_path = Path(__file__).parent.parent / "infrastructure" / "prompts" / "blog" / "artist.j2"
        content = template_path.read_text()
        assert "{% if is_first_image %}" in content
        assert "style_description" in content

    def test_render_artist_accepts_new_params(self):
        """SA8: render_artist 接受 style_anchor 和 is_first_image"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_artist(
            image_type="flowchart",
            description="测试",
            context="上下文",
            style_anchor="蓝色扁平风格",
            is_first_image=False,
        )
        assert "蓝色扁平风格" in result
        assert "风格一致性要求" in result

    def test_render_artist_first_image_prompt(self):
        """SA8b: is_first_image=True 时 prompt 包含 style_description 要求"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_artist(
            image_type="flowchart",
            description="测试",
            context="上下文",
            is_first_image=True,
        )
        assert "style_description" in result
