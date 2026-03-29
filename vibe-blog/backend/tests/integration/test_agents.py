"""
Agents 集成测试（简化版）
测试 Agent 基本功能和协作
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestAgentInitialization:
    """测试 Agent 初始化"""

    def test_writer_agent_initialization(self):
        """测试 WriterAgent 初始化"""
        from services.blog_generator.agents.writer import WriterAgent

        mock_llm = MagicMock()
        agent = WriterAgent(llm_client=mock_llm)

        assert agent is not None
        assert agent.llm == mock_llm

    def test_reviewer_agent_initialization(self):
        """测试 ReviewerAgent 初始化"""
        from services.blog_generator.agents.reviewer import ReviewerAgent

        mock_llm = MagicMock()
        agent = ReviewerAgent(llm_client=mock_llm)

        assert agent is not None
        assert agent.llm == mock_llm

    def test_artist_agent_initialization(self):
        """测试 ArtistAgent 初始化"""
        from services.blog_generator.agents.artist import ArtistAgent

        mock_llm = MagicMock()
        agent = ArtistAgent(llm_client=mock_llm)

        assert agent is not None
        assert agent.llm == mock_llm


class TestWriterAgent:
    """测试 WriterAgent"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        # Mock chat 方法返回 JSON 字符串
        client.chat.return_value = json.dumps({
            'content': 'Generated section content',
            'key_points': ['Point 1', 'Point 2']
        })
        return client

    @pytest.fixture
    def writer_agent(self, mock_llm_client):
        """创建 WriterAgent 实例"""
        from services.blog_generator.agents.writer import WriterAgent
        return WriterAgent(llm_client=mock_llm_client)

    def test_writer_agent_run(self, writer_agent):
        """测试 WriterAgent 运行"""
        from services.blog_generator.schemas.state import create_initial_state

        # 创建初始状态
        state = create_initial_state(
            topic='Vue 3 Composition API',
            article_type='tutorial',
            target_audience='intermediate',
            target_length='medium'
        )

        # 添加大纲
        state['outline'] = {
            'title': 'Vue 3 Composition API 深度解析',
            'sections': [
                {
                    'title': '什么是 Composition API',
                    'key_points': ['定义', '优势', '使用场景']
                }
            ]
        }

        # 运行 writer agent
        result = writer_agent.run(state)

        # 验证返回了更新的状态
        assert result is not None
        assert 'sections' in result

    def test_writer_agent_error_handling(self):
        """测试 WriterAgent 错误处理"""
        from services.blog_generator.agents.writer import WriterAgent

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception('LLM API error')

        agent = WriterAgent(llm_client=mock_llm)

        from services.blog_generator.schemas.state import create_initial_state
        state = create_initial_state(topic='Test', target_length='mini')
        state['outline'] = {'title': 'Test', 'sections': [{'title': 'S1', 'key_points': []}]}

        # 应该捕获错误
        try:
            result = agent.run(state)
            # 如果没有抛出异常，验证返回了合理的状态
            assert result is not None
        except Exception as e:
            # 如果抛出异常，验证是预期的错误
            assert 'LLM API error' in str(e)


class TestReviewerAgent:
    """测试 ReviewerAgent"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        client.chat.return_value = json.dumps({
            'review_score': 85,
            'review_approved': True,
            'review_issues': []
        })
        return client

    @pytest.fixture
    def reviewer_agent(self, mock_llm_client):
        """创建 ReviewerAgent 实例"""
        from services.blog_generator.agents.reviewer import ReviewerAgent
        return ReviewerAgent(llm_client=mock_llm_client)

    def test_reviewer_agent_run(self, reviewer_agent):
        """测试 ReviewerAgent 运行"""
        from services.blog_generator.schemas.state import create_initial_state

        state = create_initial_state(topic='Test', target_length='mini')
        state['outline'] = {'title': 'Test', 'sections': []}
        state['sections'] = [
            {
                'title': 'Section 1',
                'content': 'This is the content of section 1.',
                'key_points': ['Point 1']
            }
        ]

        result = reviewer_agent.run(state)

        # 验证返回了评审结果
        assert 'review_score' in result
        assert 'review_approved' in result

    def test_reviewer_agent_error_handling(self):
        """测试 ReviewerAgent 错误处理"""
        from services.blog_generator.agents.reviewer import ReviewerAgent

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception('Review failed')

        agent = ReviewerAgent(llm_client=mock_llm)

        from services.blog_generator.schemas.state import create_initial_state
        state = create_initial_state(topic='Test', target_length='mini')
        state['sections'] = []

        try:
            result = agent.run(state)
            assert result is not None
        except Exception as e:
            assert 'Review failed' in str(e)


class TestArtistAgent:
    """测试 ArtistAgent"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        client.chat.return_value = json.dumps({
            'images': []  # 简化测试，返回空列表
        })
        return client

    @pytest.fixture
    def artist_agent(self, mock_llm_client):
        """创建 ArtistAgent 实例"""
        from services.blog_generator.agents.artist import ArtistAgent
        return ArtistAgent(llm_client=mock_llm_client)

    def test_artist_agent_run(self, artist_agent):
        """测试 ArtistAgent 运行"""
        from services.blog_generator.schemas.state import create_initial_state

        state = create_initial_state(topic='Test', target_length='mini')
        state['outline'] = {'title': 'Test', 'sections': []}
        state['sections'] = [
            {'title': 'Section 1', 'content': 'Content'}
        ]
        state['images'] = []

        result = artist_agent.run(state)

        # 验证返回了状态
        assert result is not None
        assert 'images' in result

    def test_artist_agent_error_handling(self):
        """测试 ArtistAgent 错误处理"""
        from services.blog_generator.agents.artist import ArtistAgent

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception('Image generation failed')

        agent = ArtistAgent(llm_client=mock_llm)

        from services.blog_generator.schemas.state import create_initial_state
        state = create_initial_state(topic='Test', target_length='mini')
        state['sections'] = []
        state['images'] = []

        try:
            result = agent.run(state)
            assert result is not None
        except Exception as e:
            assert 'Image generation failed' in str(e)


class TestAgentCollaboration:
    """测试 Agent 协作"""

    def test_writer_reviewer_collaboration(self):
        """测试 Writer 和 Reviewer 协作"""
        from services.blog_generator.agents.writer import WriterAgent
        from services.blog_generator.agents.reviewer import ReviewerAgent
        from services.blog_generator.schemas.state import create_initial_state

        # Mock LLM 客户端
        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            'content': 'Generated content',
            'review_score': 85,
            'review_approved': True,
            'review_issues': []
        })

        writer = WriterAgent(llm_client=mock_llm)
        reviewer = ReviewerAgent(llm_client=mock_llm)

        # 初始状态
        state = create_initial_state(topic='Test', target_length='mini')
        state['outline'] = {
            'title': 'Test',
            'sections': [{'title': 'Section 1', 'key_points': ['P1']}]
        }

        # Writer 写入内容
        state = writer.run(state)
        assert 'sections' in state

        # Reviewer 评审内容
        state = reviewer.run(state)
        assert 'review_score' in state or 'review_approved' in state


# 导入 json 模块
import json
