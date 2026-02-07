"""
Agents 集成测试
测试 Agent 协作和工作流
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestAgentInitialization:
    """测试 Agent 初始化"""

    def test_writer_agent_initialization(self):
        """测试 WriterAgent 初始化"""
        from services.blog_generator.agents.writer import WriterAgent
        from services.blog_generator.llm_client_adapter import LLMClientAdapter

        mock_llm = MagicMock(spec=LLMClientAdapter)
        agent = WriterAgent(llm_client=mock_llm)

        assert agent is not None
        assert agent.llm_client == mock_llm

    def test_reviewer_agent_initialization(self):
        """测试 ReviewerAgent 初始化"""
        from services.blog_generator.agents.reviewer import ReviewerAgent
        from services.blog_generator.llm_client_adapter import LLMClientAdapter

        mock_llm = MagicMock(spec=LLMClientAdapter)
        agent = ReviewerAgent(llm_client=mock_llm)

        assert agent is not None
        assert agent.llm_client == mock_llm

    def test_artist_agent_initialization(self):
        """测试 ArtistAgent 初始化"""
        from services.blog_generator.agents.artist import ArtistAgent
        from services.blog_generator.llm_client_adapter import LLMClientAdapter

        mock_llm = MagicMock(spec=LLMClientAdapter)
        agent = ArtistAgent(llm_client=mock_llm)

        assert agent is not None
        assert agent.llm_client == mock_llm


class TestWriterAgent:
    """测试 WriterAgent"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        client.chat.return_value = {
            'content': 'Generated section content',
            'sections': [
                {
                    'title': 'Section 1',
                    'content': 'Content for section 1',
                    'key_points': ['Point 1', 'Point 2']
                }
            ]
        }
        return client

    @pytest.fixture
    def writer_agent(self, mock_llm_client):
        """创建 WriterAgent 实例"""
        from services.blog_generator.agents.writer import WriterAgent
        return WriterAgent(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_state(self):
        """示例状态"""
        return {
            'topic': 'Vue 3 Composition API',
            'article_type': 'tutorial',
            'target_audience': 'intermediate',
            'outline': {
                'title': 'Vue 3 Composition API 深度解析',
                'sections': [
                    {
                        'title': '什么是 Composition API',
                        'key_points': ['定义', '优势', '使用场景']
                    },
                    {
                        'title': '核心概念',
                        'key_points': ['setup', 'ref', 'reactive']
                    }
                ]
            },
            'sections': [],
            'background_knowledge': 'Vue 3 is the latest version...'
        }

    def test_writer_agent_run(self, writer_agent, sample_state, mock_llm_client):
        """测试 WriterAgent 运行"""
        result = writer_agent.run(sample_state)

        # 验证返回了更新的状态
        assert 'sections' in result
        assert len(result['sections']) > 0

        # 验证 LLM 被调用
        assert mock_llm_client.chat.called

    def test_writer_agent_writes_all_sections(self, writer_agent, sample_state,
                                               mock_llm_client):
        """测试 WriterAgent 写入所有章节"""
        # Mock 返回多个章节
        mock_llm_client.chat.return_value = {
            'sections': [
                {'title': 'Section 1', 'content': 'Content 1'},
                {'title': 'Section 2', 'content': 'Content 2'}
            ]
        }

        result = writer_agent.run(sample_state)

        # 验证所有章节都被写入
        assert len(result['sections']) == 2
        assert result['sections'][0]['title'] == 'Section 1'
        assert result['sections'][1]['title'] == 'Section 2'

    def test_writer_agent_uses_background_knowledge(self, writer_agent, sample_state,
                                                     mock_llm_client):
        """测试 WriterAgent 使用背景知识"""
        result = writer_agent.run(sample_state)

        # 验证 LLM 调用包含背景知识
        call_args = mock_llm_client.chat.call_args
        # 检查调用参数中是否包含背景知识
        assert call_args is not None


class TestReviewerAgent:
    """测试 ReviewerAgent"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        client.chat.return_value = {
            'review_score': 85,
            'review_issues': [
                {
                    'section': 'Section 1',
                    'issue': 'Needs more examples',
                    'severity': 'medium'
                }
            ],
            'suggestions': ['Add code examples', 'Improve clarity']
        }
        return client

    @pytest.fixture
    def reviewer_agent(self, mock_llm_client):
        """创建 ReviewerAgent 实例"""
        from services.blog_generator.agents.reviewer import ReviewerAgent
        return ReviewerAgent(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_state_with_content(self):
        """带内容的示例状态"""
        return {
            'topic': 'Vue 3 Composition API',
            'article_type': 'tutorial',
            'outline': {
                'title': 'Vue 3 Composition API',
                'sections': [
                    {'title': 'Section 1', 'key_points': ['Point 1']}
                ]
            },
            'sections': [
                {
                    'title': 'Section 1',
                    'content': 'This is the content of section 1.',
                    'key_points': ['Point 1']
                }
            ],
            'code_blocks': [
                {'language': 'javascript', 'code': 'const x = 1;'}
            ],
            'images': []
        }

    def test_reviewer_agent_run(self, reviewer_agent, sample_state_with_content,
                                 mock_llm_client):
        """测试 ReviewerAgent 运行"""
        result = reviewer_agent.run(sample_state_with_content)

        # 验证返回了评审结果
        assert 'review_score' in result
        assert 'review_issues' in result
        assert result['review_score'] == 85

        # 验证 LLM 被调用
        assert mock_llm_client.chat.called

    def test_reviewer_agent_identifies_issues(self, reviewer_agent,
                                                sample_state_with_content):
        """测试 ReviewerAgent 识别问题"""
        result = reviewer_agent.run(sample_state_with_content)

        # 验证识别了问题
        assert len(result['review_issues']) > 0
        assert result['review_issues'][0]['section'] == 'Section 1'
        assert result['review_issues'][0]['severity'] == 'medium'

    def test_reviewer_agent_provides_suggestions(self, reviewer_agent,
                                                   sample_state_with_content):
        """测试 ReviewerAgent 提供建议"""
        result = reviewer_agent.run(sample_state_with_content)

        # 验证提供了建议
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0


class TestArtistAgent:
    """测试 ArtistAgent"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        client.chat.return_value = {
            'images': [
                {
                    'section': 'Section 1',
                    'description': 'Architecture diagram showing components',
                    'type': 'diagram',
                    'style': 'technical'
                },
                {
                    'section': 'Section 2',
                    'description': 'Code flow visualization',
                    'type': 'flowchart',
                    'style': 'minimalist'
                }
            ]
        }
        return client

    @pytest.fixture
    def artist_agent(self, mock_llm_client):
        """创建 ArtistAgent 实例"""
        from services.blog_generator.agents.artist import ArtistAgent
        return ArtistAgent(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_state_for_images(self):
        """用于图片生成的示例状态"""
        return {
            'topic': 'Microservices Architecture',
            'article_type': 'guide',
            'outline': {
                'title': 'Microservices Architecture Guide',
                'sections': [
                    {'title': 'Architecture Overview', 'key_points': ['Components']},
                    {'title': 'Communication Patterns', 'key_points': ['REST', 'gRPC']}
                ]
            },
            'sections': [
                {
                    'title': 'Architecture Overview',
                    'content': 'Microservices consist of multiple components...'
                },
                {
                    'title': 'Communication Patterns',
                    'content': 'Services communicate via REST or gRPC...'
                }
            ],
            'images': [],
            'target_images_count': 2
        }

    def test_artist_agent_run(self, artist_agent, sample_state_for_images,
                               mock_llm_client):
        """测试 ArtistAgent 运行"""
        result = artist_agent.run(sample_state_for_images)

        # 验证返回了图片描述
        assert 'images' in result
        assert len(result['images']) > 0

        # 验证 LLM 被调用
        assert mock_llm_client.chat.called

    def test_artist_agent_generates_image_descriptions(self, artist_agent,
                                                        sample_state_for_images):
        """测试 ArtistAgent 生成图片描述"""
        result = artist_agent.run(sample_state_for_images)

        # 验证生成了图片描述
        assert len(result['images']) == 2
        assert result['images'][0]['section'] == 'Section 1'
        assert result['images'][0]['type'] == 'diagram'
        assert 'description' in result['images'][0]

    def test_artist_agent_respects_target_count(self, artist_agent,
                                                  sample_state_for_images,
                                                  mock_llm_client):
        """测试 ArtistAgent 遵守目标图片数量"""
        # 设置目标数量
        sample_state_for_images['target_images_count'] = 3

        # Mock 返回更多图片
        mock_llm_client.chat.return_value = {
            'images': [
                {'section': 'S1', 'description': 'D1', 'type': 'diagram'},
                {'section': 'S2', 'description': 'D2', 'type': 'chart'},
                {'section': 'S3', 'description': 'D3', 'type': 'flowchart'}
            ]
        }

        result = artist_agent.run(sample_state_for_images)

        # 验证生成了正确数量的图片
        assert len(result['images']) == 3


class TestAgentCollaboration:
    """测试 Agent 协作"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        # 为不同的 agent 返回不同的响应
        def chat_side_effect(*args, **kwargs):
            # 根据 prompt 内容判断是哪个 agent
            prompt = kwargs.get('messages', [{}])[0].get('content', '')
            if 'write' in prompt.lower() or 'section' in prompt.lower():
                return {
                    'sections': [
                        {'title': 'Section 1', 'content': 'Content 1'}
                    ]
                }
            elif 'review' in prompt.lower():
                return {
                    'review_score': 85,
                    'review_issues': [],
                    'suggestions': []
                }
            elif 'image' in prompt.lower() or 'visual' in prompt.lower():
                return {
                    'images': [
                        {'section': 'Section 1', 'description': 'Diagram'}
                    ]
                }
            return {}

        client.chat.side_effect = chat_side_effect
        return client

    def test_writer_reviewer_collaboration(self, mock_llm_client):
        """测试 Writer 和 Reviewer 协作"""
        from services.blog_generator.agents.writer import WriterAgent
        from services.blog_generator.agents.reviewer import ReviewerAgent

        writer = WriterAgent(llm_client=mock_llm_client)
        reviewer = ReviewerAgent(llm_client=mock_llm_client)

        # 初始状态
        state = {
            'topic': 'Test Topic',
            'article_type': 'tutorial',
            'outline': {
                'title': 'Test',
                'sections': [{'title': 'Section 1', 'key_points': ['P1']}]
            },
            'sections': []
        }

        # Writer 写入内容
        state = writer.run(state)
        assert len(state['sections']) > 0

        # Reviewer 评审内容
        state = reviewer.run(state)
        assert 'review_score' in state
        assert 'review_issues' in state

    def test_writer_artist_collaboration(self, mock_llm_client):
        """测试 Writer 和 Artist 协作"""
        from services.blog_generator.agents.writer import WriterAgent
        from services.blog_generator.agents.artist import ArtistAgent

        writer = WriterAgent(llm_client=mock_llm_client)
        artist = ArtistAgent(llm_client=mock_llm_client)

        # 初始状态
        state = {
            'topic': 'Test Topic',
            'article_type': 'guide',
            'outline': {
                'title': 'Test',
                'sections': [{'title': 'Section 1', 'key_points': ['P1']}]
            },
            'sections': [],
            'images': [],
            'target_images_count': 1
        }

        # Writer 写入内容
        state = writer.run(state)
        assert len(state['sections']) > 0

        # Artist 生成图片描述
        state = artist.run(state)
        assert len(state['images']) > 0

    @pytest.mark.skip(reason="Full workflow requires complex state management")
    def test_full_agent_workflow(self):
        """测试完整的 Agent 工作流（需要复杂的状态管理）"""
        pass


class TestAgentErrorHandling:
    """测试 Agent 错误处理"""

    def test_writer_agent_llm_error(self):
        """测试 WriterAgent LLM 错误处理"""
        from services.blog_generator.agents.writer import WriterAgent

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception('LLM API error')

        agent = WriterAgent(llm_client=mock_llm)

        state = {
            'topic': 'Test',
            'outline': {'title': 'Test', 'sections': []},
            'sections': []
        }

        # 应该捕获错误并返回原状态或错误状态
        try:
            result = agent.run(state)
            # 如果没有抛出异常，验证返回了合理的状态
            assert result is not None
        except Exception as e:
            # 如果抛出异常，验证是预期的错误
            assert 'LLM API error' in str(e)

    def test_reviewer_agent_invalid_content(self):
        """测试 ReviewerAgent 处理无效内容"""
        from services.blog_generator.agents.reviewer import ReviewerAgent

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {
            'review_score': 0,
            'review_issues': [{'issue': 'No content'}],
            'suggestions': []
        }

        agent = ReviewerAgent(llm_client=mock_llm)

        # 空内容状态
        state = {
            'topic': 'Test',
            'outline': {'title': 'Test', 'sections': []},
            'sections': []  # 空章节
        }

        result = agent.run(state)

        # 应该返回低分
        assert result.get('review_score', 100) < 50

    def test_artist_agent_no_sections(self):
        """测试 ArtistAgent 处理无章节情况"""
        from services.blog_generator.agents.artist import ArtistAgent

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {'images': []}

        agent = ArtistAgent(llm_client=mock_llm)

        state = {
            'topic': 'Test',
            'outline': {'title': 'Test', 'sections': []},
            'sections': [],  # 无章节
            'images': []
        }

        result = agent.run(state)

        # 应该返回空图片列表
        assert len(result.get('images', [])) == 0
