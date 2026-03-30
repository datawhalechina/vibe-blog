"""
BlogService 集成测试
测试博客生成服务的核心逻辑和工作流
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import asyncio


class TestBlogServiceInitialization:
    """测试 BlogService 初始化"""

    def test_blog_service_initialization(self):
        """测试服务初始化"""
        from services.blog_generator.blog_service import BlogService

        # Mock LLM 客户端
        mock_llm_client = MagicMock()

        # 创建服务
        service = BlogService(llm_client=mock_llm_client)

        assert service is not None
        assert service.generator is not None
        assert service.knowledge_service is None  # 默认为 None


class TestBlogServiceGeneration:
    """测试博客生成流程"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = MagicMock()
        client.chat.return_value = "Generated content"
        return client

    @pytest.fixture
    def blog_service(self, mock_llm_client):
        """创建 BlogService 实例"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(llm_client=mock_llm_client)
        return service

    def test_generate_sync_basic(self, blog_service):
        """测试同步生成基本流程"""
        # Mock BlogGenerator.generate
        with patch.object(blog_service.generator, 'generate') as mock_generate:
            mock_generate.return_value = {
                'final_markdown': '# Test Blog\n\nContent',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [{'title': 'Section 1', 'content': 'Content'}],
                'code_blocks': [],
                'images': [],
                'review_score': 85
            }

            result = blog_service.generate_sync(
                topic='Test Topic',
                article_type='tutorial',
                target_audience='intermediate',
                target_length='medium'
            )

            # 验证结果 - generate_sync 直接返回 generator.generate() 的结果
            assert result is not None
            assert 'final_markdown' in result
            assert result['final_markdown'] == '# Test Blog\n\nContent'
            assert len(result['sections']) == 1
            assert result['review_score'] == 85

            # 验证 generator 被调用
            mock_generate.assert_called_once()

    def test_generate_sync_with_source_material(self, blog_service):
        """测试带源材料的生成"""
        with patch.object(blog_service.generator, 'generate') as mock_generate:
            mock_generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            result = blog_service.generate_sync(
                topic='Test Topic',
                source_material='Reference material here'
            )

            assert result is not None
            assert 'final_markdown' in result

            # 验证 source_material 被传递
            call_kwargs = mock_generate.call_args[1]
            assert 'source_material' in call_kwargs

    def test_generate_sync_error_handling(self, blog_service):
        """测试生成错误处理"""
        with patch.object(blog_service.generator, 'generate') as mock_generate:
            mock_generate.side_effect = Exception('Generation failed')

            # generate_sync 不捕获异常，会直接抛出
            with pytest.raises(Exception) as exc_info:
                blog_service.generate_sync(topic='Test Topic')

            assert 'Generation failed' in str(exc_info.value)

    @pytest.mark.skip(reason="Async generation requires complex mocking")
    def test_generate_async_creates_task(self, blog_service):
        """测试异步生成创建任务（需要复杂 mock）"""
        pass

    @pytest.mark.skip(reason="Async generation requires thread mocking")
    def test_generate_async_execution(self, blog_service):
        """测试异步生成执行（需要线程 mock）"""
        pass


class TestBlogServiceCoverGeneration:
    """测试封面生成功能"""

    @pytest.mark.skip(reason="Cover image generation requires complex service initialization mocking")
    def test_generate_cover_image(self):
        """测试生成封面图片（需要复杂的服务初始化 mock）"""
        # 封面图生成涉及多个服务的初始化和交互，包括：
        # - get_image_service() 全局函数调用
        # - extract_article_summary() LLM 调用
        # - ImageService.generate() 方法调用
        # 这些依赖关系复杂，需要更完整的集成测试环境
        pass

    @pytest.mark.skip(reason="Cover video generation requires complex service initialization mocking")
    def test_generate_cover_video(self):
        """测试生成封面视频（需要复杂的服务初始化 mock）"""
        # 封面视频生成涉及多个服务的初始化和交互，包括：
        # - get_video_service() 全局函数调用
        # - get_oss_service() 全局函数调用
        # - VideoService.generate_from_image() 方法调用
        # 这些依赖关系复杂，需要更完整的集成测试环境
        pass


class TestBlogServiceDatabaseIntegration:
    """测试数据库集成"""

    @pytest.mark.skip(reason="Database integration requires full service setup")
    def test_save_to_database(self):
        """测试保存到数据库（需要完整服务设置）"""
        pass

    @pytest.mark.skip(reason="Database integration requires full service setup")
    def test_skip_database_save(self):
        """测试跳过数据库保存（需要完整服务设置）"""
        pass


class TestBlogServiceConfiguration:
    """测试配置和参数处理"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        return MagicMock()

    @pytest.fixture
    def blog_service(self, mock_llm_client):
        """创建 BlogService 实例"""
        from services.blog_generator.blog_service import BlogService
        return BlogService(llm_client=mock_llm_client)

    def test_article_type_configuration(self, blog_service):
        """测试文章类型配置"""
        with patch.object(blog_service.generator, 'generate') as mock_generate:
            mock_generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            # 测试不同的文章类型
            for article_type in ['tutorial', 'guide', 'analysis', 'reference']:
                result = blog_service.generate_sync(
                    topic='Test Topic',
                    article_type=article_type
                )

                assert result is not None
                assert 'final_markdown' in result

                # 验证 article_type 被传递
                call_kwargs = mock_generate.call_args[1]
                assert call_kwargs['article_type'] == article_type

    def test_target_length_configuration(self, blog_service):
        """测试目标长度配置"""
        with patch.object(blog_service.generator, 'generate') as mock_generate:
            mock_generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            # 测试不同的长度
            for length in ['mini', 'short', 'medium', 'long']:
                result = blog_service.generate_sync(
                    topic='Test Topic',
                    target_length=length
                )

                assert result is not None
                assert 'final_markdown' in result

                # 验证 target_length 被传递
                call_kwargs = mock_generate.call_args[1]
                assert call_kwargs['target_length'] == length

    def test_target_audience_configuration(self, blog_service):
        """测试目标受众配置"""
        with patch.object(blog_service.generator, 'generate') as mock_generate:
            mock_generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            # 测试不同的受众
            for audience in ['beginner', 'intermediate', 'advanced', 'expert']:
                result = blog_service.generate_sync(
                    topic='Test Topic',
                    target_audience=audience
                )

                assert result is not None
                assert 'final_markdown' in result

                # 验证 target_audience 被传递
                call_kwargs = mock_generate.call_args[1]
                assert call_kwargs['target_audience'] == audience
