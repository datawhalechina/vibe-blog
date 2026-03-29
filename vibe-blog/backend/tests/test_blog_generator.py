"""
博客生成器测试
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


class TestPromptManager:
    """测试 Prompt 管理器"""
    
    def test_prompt_manager_singleton(self):
        """测试单例模式"""
        from services.blog_generator.prompts import get_prompt_manager
        
        pm1 = get_prompt_manager()
        pm2 = get_prompt_manager()
        
        assert pm1 is pm2
    
    def test_render_planner_prompt(self):
        """测试 Planner Prompt 渲染"""
        from services.blog_generator.prompts import get_prompt_manager
        
        pm = get_prompt_manager()
        prompt = pm.render_planner(
            topic="LangGraph 入门",
            article_type="tutorial",
            target_audience="intermediate",
            target_length="medium",
            background_knowledge="LangGraph 是一个工作流引擎",
            key_concepts=["Agent", "State", "Graph"]
        )
        
        assert "LangGraph 入门" in prompt
        assert "tutorial" in prompt
        assert "intermediate" in prompt
        assert "Agent" in prompt
    
    def test_render_writer_prompt(self):
        """测试 Writer Prompt 渲染"""
        from services.blog_generator.prompts import get_prompt_manager
        
        pm = get_prompt_manager()
        prompt = pm.render_writer(
            section_outline={
                "id": "section_1",
                "title": "什么是 LangGraph",
                "key_concept": "工作流引擎"
            },
            previous_section_summary="这是第一章",
            next_section_preview="下一章介绍安装",
            background_knowledge="背景知识"
        )
        
        assert "什么是 LangGraph" in prompt
        assert "工作流引擎" in prompt


class TestSharedState:
    """测试共享状态"""
    
    def test_create_initial_state(self):
        """测试创建初始状态"""
        from services.blog_generator.schemas.state import create_initial_state
        
        state = create_initial_state(
            topic="测试主题",
            article_type="tutorial",
            target_audience="beginner",
            target_length="short"
        )
        
        assert state['topic'] == "测试主题"
        assert state['article_type'] == "tutorial"
        assert state['target_audience'] == "beginner"
        assert state['target_length'] == "short"
        assert state['sections'] == []
        assert state['code_blocks'] == []
        assert state['images'] == []


class TestHelpers:
    """测试工具函数"""
    
    def test_deduplicate_by_url(self):
        """测试 URL 去重"""
        from services.blog_generator.utils.helpers import deduplicate_by_url
        
        results = [
            {"url": "http://a.com", "title": "A"},
            {"url": "http://b.com", "title": "B"},
            {"url": "http://a.com", "title": "A duplicate"},
        ]
        
        unique = deduplicate_by_url(results)
        
        assert len(unique) == 2
        assert unique[0]['title'] == "A"
        assert unique[1]['title'] == "B"
    
    def test_generate_anchor_id(self):
        """测试锚点 ID 生成"""
        from services.blog_generator.utils.helpers import generate_anchor_id
        
        anchor = generate_anchor_id("什么是 LangGraph？")
        
        assert " " not in anchor
        assert "？" not in anchor
    
    def test_estimate_reading_time(self):
        """测试阅读时间估算"""
        from services.blog_generator.utils.helpers import estimate_reading_time
        
        # 中文文本
        chinese_text = "这是一段中文测试文本" * 100
        time = estimate_reading_time(chinese_text)
        
        assert time > 0
        
        # 英文文本
        english_text = "This is a test " * 100
        time = estimate_reading_time(english_text)
        
        assert time > 0


class TestAgents:
    """测试各 Agent"""
    
    def test_researcher_agent_init(self):
        """测试 Researcher Agent 初始化"""
        from services.blog_generator.agents import ResearcherAgent
        
        mock_llm = Mock()
        agent = ResearcherAgent(mock_llm)
        
        assert agent.llm == mock_llm
        assert agent.search_service is None
    
    def test_planner_agent_init(self):
        """测试 Planner Agent 初始化"""
        from services.blog_generator.agents import PlannerAgent
        
        mock_llm = Mock()
        agent = PlannerAgent(mock_llm)
        
        assert agent.llm == mock_llm
    
    def test_writer_agent_init(self):
        """测试 Writer Agent 初始化"""
        from services.blog_generator.agents import WriterAgent
        
        mock_llm = Mock()
        agent = WriterAgent(mock_llm)
        
        assert agent.llm == mock_llm
    
    def test_assembler_agent_init(self):
        """测试 Assembler Agent 初始化"""
        from services.blog_generator.agents import AssemblerAgent
        
        agent = AssemblerAgent()
        
        assert agent is not None


class TestBlogGenerator:
    """测试博客生成器"""
    
    def test_generator_init(self):
        """测试生成器初始化"""
        from services.blog_generator import BlogGenerator
        
        mock_llm = Mock()
        generator = BlogGenerator(mock_llm)
        
        assert generator.llm == mock_llm
        assert generator.workflow is not None
    
    def test_generator_compile(self):
        """测试工作流编译"""
        from services.blog_generator import BlogGenerator
        
        mock_llm = Mock()
        generator = BlogGenerator(mock_llm)
        app = generator.compile()
        
        assert app is not None
        assert generator.app is not None


class MockLLMClient:
    """模拟 LLM 客户端"""
    
    def chat(self, messages, response_format=None):
        """模拟 chat 方法"""
        if response_format and response_format.get('type') == 'json_object':
            return json.dumps({
                "title": "测试标题",
                "sections": [
                    {"id": "section_1", "title": "章节1"}
                ]
            })
        return "这是模拟的 LLM 响应"


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.skip(reason="需要真实 LLM 服务")
    def test_full_generation_flow(self):
        """测试完整生成流程"""
        from services.blog_generator import BlogGenerator
        
        llm = MockLLMClient()
        generator = BlogGenerator(llm)
        
        result = generator.generate(
            topic="Python 入门",
            article_type="tutorial",
            target_audience="beginner",
            target_length="short"
        )
        
        assert result['success'] is True
        assert 'markdown' in result


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
