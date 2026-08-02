"""
Mini 博客 v2 单元测试

测试内容：
1. Mini 模式修订轮数限制
2. 字数统计辅助函数
3. _should_revise 条件判断
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestWordCountHelpers:
    """测试字数统计辅助函数"""
    
    def test_get_content_word_count_empty(self):
        """测试空 state"""
        from services.blog_generator.orchestrator.nodes.writing import _content_word_count
        
        state = {'sections': []}
        assert _content_word_count(state) == 0
    
    def test_get_content_word_count_with_content(self):
        """测试有内容的 state"""
        from services.blog_generator.orchestrator.nodes.writing import _content_word_count
        
        state = {
            'sections': [
                {'content': '这是第一章的内容'},  # 8 字
                {'content': '这是第二章'},  # 5 字
                {'content': ''},  # 0 字
            ]
        }
        assert _content_word_count(state) == 13
    
    def test_get_content_word_count_no_sections(self):
        """测试没有 sections 字段"""
        from services.blog_generator.orchestrator.nodes.writing import _content_word_count
        
        state = {}
        assert _content_word_count(state) == 0
    
    def test_log_word_count_diff_positive(self, caplog):
        """测试字数增加的日志"""
        import logging
        from services.blog_generator.orchestrator.nodes.writing import _log_word_count_diff
        
        with caplog.at_level(logging.INFO):
            _log_word_count_diff("Writer", 100, 500)
        
        assert "📊 [Writer] 字数变化: 100 → 500 (+400 字)" in caplog.text
    
    def test_log_word_count_diff_negative(self, caplog):
        """测试字数减少的日志"""
        import logging
        from services.blog_generator.orchestrator.nodes.writing import _log_word_count_diff
        
        with caplog.at_level(logging.INFO):
            _log_word_count_diff("修订", 500, 400)
        
        assert "📊 [修订] 字数变化: 500 → 400 (-100 字)" in caplog.text


class TestMiniModeRevisionLimit:
    """测试 Mini 模式修订轮数限制"""
    
    @pytest.fixture
    def mock_generator(self):
        """创建 mock 的 BlogGenerator"""
        from services.blog_generator.generator import BlogGenerator
        
        mock_llm = Mock()
        generator = BlogGenerator(mock_llm)
        return generator
    
    def test_mini_mode_first_revision_with_high_issues(self, mock_generator):
        """Mini 模式：第一次修订，有 high 问题 → 应该修订"""
        state = {
            'target_length': 'mini',
            'revision_count': 0,
            'review_issues': [
                {'severity': 'high', 'description': '问题1'},
                {'severity': 'medium', 'description': '问题2'},
            ]
        }
        
        result = mock_generator._should_revise(state)
        
        assert result == "revision"
        # 验证只保留 high 级别问题
        assert len(state['review_issues']) == 1
        assert state['review_issues'][0]['severity'] == 'high'
    
    def test_mini_mode_second_revision_skip(self, mock_generator):
        """Mini 模式：已修订 1 轮 → 跳过修订"""
        state = {
            'target_length': 'mini',
            'revision_count': 1,  # 已修订 1 轮
            'review_issues': [
                {'severity': 'high', 'description': '问题1'},
            ]
        }
        
        result = mock_generator._should_revise(state)
        
        assert result == "assemble"
    
    def test_mini_mode_no_high_issues(self, mock_generator):
        """Mini 模式：没有 high 问题 → 跳过修订"""
        state = {
            'target_length': 'mini',
            'revision_count': 0,
            'review_issues': [
                {'severity': 'medium', 'description': '问题1'},
                {'severity': 'low', 'description': '问题2'},
            ]
        }
        
        result = mock_generator._should_revise(state)
        
        assert result == "assemble"
    
    def test_short_mode_same_as_mini(self, mock_generator):
        """Short 模式：与 Mini 模式行为一致"""
        state = {
            'target_length': 'short',
            'revision_count': 1,  # 已修订 1 轮
            'review_issues': [
                {'severity': 'high', 'description': '问题1'},
            ]
        }
        
        result = mock_generator._should_revise(state)
        
        assert result == "assemble"
    
    def test_medium_mode_allows_multiple_revisions(self, mock_generator):
        """Medium 模式：允许多轮修订"""
        state = {
            'target_length': 'medium',
            'revision_count': 1,
            'review_approved': False,
            'review_issues': [
                {'severity': 'high', 'description': '问题1'},
            ]
        }
        
        result = mock_generator._should_revise(state)
        
        # medium 模式使用 max_revision_rounds (默认 3)
        assert result == "revision"
    
    def test_medium_mode_max_revisions_reached(self, mock_generator):
        """Medium 模式：达到最大修订轮数"""
        state = {
            'target_length': 'medium',
            'revision_count': 3,  # 已达到默认最大值
            'review_approved': False,
            'review_issues': [
                {'severity': 'high', 'description': '问题1'},
            ]
        }
        
        result = mock_generator._should_revise(state)
        
        assert result == "assemble"


class TestPromptLogging:
    """测试 Prompt 日志输出"""
    
    def test_writer_prompt_logging(self, caplog):
        """测试 Writer Prompt 日志"""
        import logging
        from services.blog_generator.agents.writer import WriterAgent
        from services.blog_generator.prompts import get_prompt_manager
        
        # 只测试 Prompt 生成，不调用 LLM
        pm = get_prompt_manager()
        prompt = pm.render_writer(
            section_outline={
                "id": "section_1",
                "title": "测试章节",
                "key_concept": "测试概念"
            },
            previous_section_summary="",
            next_section_preview="",
            background_knowledge="背景知识"
        )
        
        # 验证 Prompt 生成成功
        assert "测试章节" in prompt
        assert len(prompt) > 100
    
    def test_reviewer_prompt_logging(self, caplog):
        """测试 Reviewer Prompt 日志"""
        import logging
        from services.blog_generator.prompts import get_prompt_manager
        
        pm = get_prompt_manager()
        prompt = pm.render_reviewer(
            document="# 测试文档\n\n这是测试内容",
            outline={
                "title": "测试大纲",
                "sections": []
            },
            search_results=[],
            verbatim_data=[],
            learning_objectives=[],
            background_knowledge="背景知识"
        )
        
        # 验证 Prompt 生成成功
        assert "测试文档" in prompt
        assert len(prompt) > 100


class TestWriterCorrect:
    """测试 Writer 更正功能"""
    
    def test_render_writer_correct(self):
        """测试 render_writer_correct 方法"""
        from services.blog_generator.prompts import get_prompt_manager
        
        pm = get_prompt_manager()
        prompt = pm.render_writer_correct(
            section_title="测试章节",
            original_content="这是原始内容，包含一些错误信息。",
            issues=[
                {
                    "severity": "high",
                    "description": "虚构了不存在的数据",
                    "affected_content": "错误信息"
                }
            ]
        )
        
        # 验证 Prompt 包含关键内容
        assert "测试章节" in prompt
        assert "原始内容" in prompt
        assert "虚构" in prompt
        assert "只更正，不扩展" in prompt
    
    def test_render_writer_correct_empty_issues(self):
        """测试空问题列表"""
        from services.blog_generator.prompts import get_prompt_manager
        
        pm = get_prompt_manager()
        prompt = pm.render_writer_correct(
            section_title="测试章节",
            original_content="这是原始内容",
            issues=[]
        )
        
        # 即使没有问题，也应该生成有效的 Prompt
        assert "测试章节" in prompt
        assert len(prompt) > 100


class TestMiniModeCorrectSection:
    """测试 Mini 模式使用 correct_section 而非 enhance_section"""
    
    def test_revision_node_uses_correct_section_for_mini(self):
        """测试 Mini 模式修订使用 correct_section"""
        # 验证 generator.py 中的修订逻辑
        import inspect
        from services.blog_generator.orchestrator.nodes.review import (
            revision_correct_only,
            revision_node,
        )

        # _revision_node 委托给 _revision_correct_only（correct_only 策略）
        source_node = inspect.getsource(revision_node)
        assert "revision_strategy" in source_node
        assert "correct_only" in source_node

        # _revision_correct_only 中实际调用 correct_section
        source_correct = inspect.getsource(revision_correct_only)
        assert "correct_section" in source_correct


class TestInitialState:
    """测试初始状态创建"""
    
    def test_mini_mode_max_search_count(self):
        """测试 Mini 模式的 max_search_count"""
        from services.blog_generator.schemas.state import create_initial_state
        
        state = create_initial_state(
            topic="测试主题",
            article_type="tutorial",
            target_audience="beginner",
            target_length="mini"
        )
        
        # Mini 模式应该有较小的 max_search_count
        assert state['max_search_count'] <= 2
    
    def test_medium_mode_max_search_count(self):
        """测试 Medium 模式的 max_search_count"""
        from services.blog_generator.schemas.state import create_initial_state
        
        state = create_initial_state(
            topic="测试主题",
            article_type="tutorial",
            target_audience="beginner",
            target_length="medium"
        )
        
        # Medium 模式应该有较大的 max_search_count
        assert state['max_search_count'] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
