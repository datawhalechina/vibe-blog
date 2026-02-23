"""Prompt 增强器单元测试 — 自动优化用户输入 prompt + 意图识别 + 关键词扩展"""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPromptEnhancerNode:
    """核心增强节点测试"""

    def _make_state(self, prompt="测试主题", **kwargs):
        return {
            "prompt": prompt, "context": "", "article_style": None,
            "locale": "zh-CN", "output": "", **kwargs,
        }

    def _mock_llm(self, response_text):
        llm = MagicMock()
        llm.chat.return_value = response_text
        return llm

    def setup_method(self):
        from services.blog_generator.prompt_enhancer.enhancer_node import (
            prompt_enhancer_node,
            _XML_PATTERN,
            _PREFIXES_TO_REMOVE,
        )
        self.prompt_enhancer_node = prompt_enhancer_node
        self._XML_PATTERN = _XML_PATTERN
        self._PREFIXES_TO_REMOVE = _PREFIXES_TO_REMOVE

    # --- XML 解析测试 ---

    def test_xml_extraction(self):
        """XML 标签正常提取"""
        llm = self._mock_llm(
            "思考过程...\n<enhanced_prompt>\n增强后的主题\n</enhanced_prompt>\n"
        )
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"] == "增强后的主题"

    def test_xml_multiline(self):
        """多行 XML 内容"""
        llm = self._mock_llm(
            "<enhanced_prompt>\n第一行\n第二行\n第三行\n</enhanced_prompt>"
        )
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert "第一行" in result["output"]
        assert "第三行" in result["output"]

    def test_xml_with_whitespace(self):
        """XML 标签内含多余空白"""
        llm = self._mock_llm(
            "\n<enhanced_prompt>\n\n  带空白的增强  \n\n</enhanced_prompt>\n"
        )
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"] == "带空白的增强"

    def test_xml_with_special_characters(self):
        """XML 内含特殊字符"""
        llm = self._mock_llm(
            '<enhanced_prompt>Python 3.12 的 TypeVar & Generic 详解</enhanced_prompt>'
        )
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert "TypeVar & Generic" in result["output"]

    def test_malformed_xml_fallback(self):
        """畸形 XML 触发 fallback"""
        llm = self._mock_llm("<enhanced_prompt>\n未闭合标签\n<enhanced_prompt>")
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"]  # 不为空即可

    # --- Fallback 前缀移除测试 ---

    def test_prefix_removal_english(self):
        """移除英文前缀"""
        llm = self._mock_llm("Enhanced Prompt: 优化后的内容")
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"] == "优化后的内容"

    def test_prefix_removal_chinese(self):
        """移除中文前缀"""
        llm = self._mock_llm("优化后的主题：深入理解 Python 异步编程")
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"] == "深入理解 Python 异步编程"

    def test_no_prefix_passthrough(self):
        """无前缀直接返回"""
        llm = self._mock_llm("深入理解 Python 异步编程的核心原理与实战")
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"] == "深入理解 Python 异步编程的核心原理与实战"

    # --- 错误处理测试 ---

    def test_empty_response(self):
        """空响应返回原始 prompt"""
        llm = self._mock_llm("")
        result = self.prompt_enhancer_node(self._make_state("原始主题"), llm)
        assert result["output"] == "原始主题"

    def test_whitespace_only_response(self):
        """纯空白响应返回原始 prompt"""
        llm = self._mock_llm("   \n\t  ")
        result = self.prompt_enhancer_node(self._make_state("原始主题"), llm)
        assert result["output"] == "原始主题"

    def test_exception_returns_original(self):
        """LLM 异常返回原始 prompt"""
        llm = MagicMock()
        llm.chat.side_effect = Exception("LLM error")
        result = self.prompt_enhancer_node(self._make_state("原始主题"), llm)
        assert result["output"] == "原始主题"

    # --- 上下文注入测试 ---

    def test_context_passed_to_template(self):
        """上下文信息传递到模板渲染"""
        llm = self._mock_llm("<enhanced_prompt>带上下文的增强</enhanced_prompt>")
        state = self._make_state(context="这是一篇关于 AI 的文章")
        result = self.prompt_enhancer_node(state, llm)
        assert result["output"] == "带上下文的增强"
        # 验证 LLM 被调用
        llm.chat.assert_called_once()

    def test_article_style_passed_to_template(self):
        """文章风格传递到模板渲染"""
        llm = self._mock_llm("<enhanced_prompt>教程风格增强</enhanced_prompt>")
        state = self._make_state(article_style="tutorial")
        result = self.prompt_enhancer_node(state, llm)
        assert result["output"] == "教程风格增强"

    def test_very_long_response(self):
        """超长响应正常处理"""
        long_content = "A" * 5000
        llm = self._mock_llm(f"<enhanced_prompt>{long_content}</enhanced_prompt>")
        result = self.prompt_enhancer_node(self._make_state(), llm)
        assert result["output"] == long_content


class TestXMLPattern:
    """XML 正则模式测试"""

    def setup_method(self):
        from services.blog_generator.prompt_enhancer.enhancer_node import _XML_PATTERN
        self._XML_PATTERN = _XML_PATTERN

    def test_basic_match(self):
        assert self._XML_PATTERN.search("<enhanced_prompt>test</enhanced_prompt>")

    def test_multiline_match(self):
        text = "<enhanced_prompt>\nline1\nline2\n</enhanced_prompt>"
        match = self._XML_PATTERN.search(text)
        assert match and "line1" in match.group(1)

    def test_no_match(self):
        assert self._XML_PATTERN.search("no xml here") is None

    def test_nested_content(self):
        text = "<enhanced_prompt>含有 <code>代码</code> 的内容</enhanced_prompt>"
        match = self._XML_PATTERN.search(text)
        assert match and "<code>代码</code>" in match.group(1)


class TestPromptEnhancerGraph:
    """子图集成测试"""

    def test_graph_invoke(self):
        """子图正常调用"""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "<enhanced_prompt>增强结果</enhanced_prompt>"
        from services.blog_generator.prompt_enhancer.builder import (
            build_prompt_enhancer_graph,
        )
        graph = build_prompt_enhancer_graph(mock_llm)
        result = graph.invoke({
            "prompt": "Python 异步编程",
            "context": "",
            "article_style": None,
            "locale": "zh-CN",
            "output": "",
        })
        assert result["output"] == "增强结果"

    def test_graph_fallback_on_error(self):
        """LLM 异常时子图返回原始 prompt"""
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception("timeout")
        from services.blog_generator.prompt_enhancer.builder import (
            build_prompt_enhancer_graph,
        )
        graph = build_prompt_enhancer_graph(mock_llm)
        result = graph.invoke({
            "prompt": "原始主题",
            "context": "",
            "article_style": None,
            "locale": "zh-CN",
            "output": "",
        })
        assert result["output"] == "原始主题"
