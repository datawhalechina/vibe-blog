"""
37.16 博客衍生物体系 — 单元测试
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.skills.registry import SkillRegistry


SAMPLE_MARKDOWN = """# AI 入门指南

## 1. 什么是人工智能
人工智能（AI）是计算机科学的一个分支，致力于创建能够模拟人类智能的系统。

## 2. 机器学习基础
机器学习是 AI 的核心方法，通过数据训练模型来做出预测。

### 2.1 监督学习
使用标注数据训练模型，如分类和回归。

### 2.2 无监督学习
从未标注数据中发现模式，如聚类和降维。

## 3. 深度学习
深度学习使用多层神经网络处理复杂任务，如图像识别和自然语言处理。
"""


class TestMindMapSkill:

    def setup_method(self):
        SkillRegistry._skills.clear()
        # 导入以触发注册
        import services.blog_generator.skills.mindmap  # noqa: F401

    def test_registered(self):
        defn = SkillRegistry.get_skill("mindmap")
        assert defn is not None
        assert defn.input_type == "markdown"
        assert defn.output_type == "json"
        assert defn.post_process is True

    def test_generate_mindmap_structure(self):
        from services.blog_generator.skills.mindmap import generate_mindmap_from_markdown
        result = generate_mindmap_from_markdown(SAMPLE_MARKDOWN)
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) > 0
        # 根节点应该是标题
        root = result["nodes"][0]
        assert "label" in root


class TestFlashcardSkill:

    def setup_method(self):
        SkillRegistry._skills.clear()
        import services.blog_generator.skills.flashcard  # noqa: F401

    def test_registered(self):
        defn = SkillRegistry.get_skill("flashcard")
        assert defn is not None
        assert defn.input_type == "markdown"
        assert defn.output_type == "json"
        assert defn.post_process is True

    def test_generate_flashcards_structure(self):
        from services.blog_generator.skills.flashcard import generate_flashcards_from_markdown
        result = generate_flashcards_from_markdown(SAMPLE_MARKDOWN)
        assert "cards" in result
        assert len(result["cards"]) > 0
        card = result["cards"][0]
        assert "question" in card
        assert "answer" in card


class TestStudyNoteSkill:

    def setup_method(self):
        SkillRegistry._skills.clear()
        import services.blog_generator.skills.study_note  # noqa: F401

    def test_registered(self):
        defn = SkillRegistry.get_skill("study_note")
        assert defn is not None
        assert defn.input_type == "markdown"
        assert defn.output_type == "markdown"
        assert defn.post_process is True

    def test_generate_study_note_structure(self):
        from services.blog_generator.skills.study_note import generate_study_note_from_markdown
        result = generate_study_note_from_markdown(SAMPLE_MARKDOWN)
        assert "note" in result
        assert len(result["note"]) > 0
        assert "key_points" in result
        assert len(result["key_points"]) > 0


class TestAllDerivativesRegistered:

    def setup_method(self):
        SkillRegistry._skills.clear()
        # Force re-registration by reloading modules
        import importlib
        import services.blog_generator.skills.mindmap as mm
        import services.blog_generator.skills.flashcard as fc
        import services.blog_generator.skills.study_note as sn
        importlib.reload(mm)
        importlib.reload(fc)
        importlib.reload(sn)

    def test_three_post_process_skills(self):
        pp = SkillRegistry.get_post_process_skills(auto_only=False)
        names = {s.name for s in pp}
        assert names == {"mindmap", "flashcard", "study_note"}

    def test_none_auto_run(self):
        pp = SkillRegistry.get_post_process_skills(auto_only=True)
        assert len(pp) == 0
