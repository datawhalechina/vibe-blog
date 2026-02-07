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
        from services.llm_service import LLMService
        from services.database_service import DatabaseService

        # Mock 依赖
        mock_llm = MagicMock(spec=LLMService)
        mock_db = MagicMock(spec=DatabaseService)

        # 创建服务
        service = BlogService(
            llm_service=mock_llm,
            db_service=mock_db
        )

        assert service is not None
        assert service.llm_service == mock_llm
        assert service.db_service == mock_db


class TestBlogServiceGeneration:
    """测试博客生成流程"""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM 服务"""
        service = MagicMock()
        service.chat.return_value = "Generated content"
        service.chat_stream.return_value = iter(["Generated ", "content"])
        return service

    @pytest.fixture
    def mock_db_service(self):
        """Mock 数据库服务"""
        service = MagicMock()
        service.save_history.return_value = "test-history-id"
        return service

    @pytest.fixture
    def mock_image_service(self):
        """Mock 图片服务"""
        service = MagicMock()
        service.generate_image.return_value = "https://example.com/image.jpg"
        return service

    @pytest.fixture
    def mock_video_service(self):
        """Mock 视频服务"""
        service = MagicMock()
        service.generate_video.return_value = "https://example.com/video.mp4"
        return service

    @pytest.fixture
    def blog_service(self, mock_llm_service, mock_db_service):
        """创建 BlogService 实例"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(
            llm_service=mock_llm_service,
            db_service=mock_db_service
        )
        return service

    def test_generate_sync_basic(self, blog_service, mock_llm_service):
        """测试同步生成基本流程"""
        # Mock BlogGenerator
        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
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

            # 验证结果
            assert result['success'] is True
            assert 'markdown' in result
            assert result['sections_count'] == 1
            assert result['review_score'] == 85

            # 验证 generator 被调用
            mock_generator.generate.assert_called_once()

    def test_generate_sync_with_source_material(self, blog_service):
        """测试带源材料的生成"""
        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
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

            assert result['success'] is True

            # 验证 source_material 被传递
            call_kwargs = mock_generator.generate.call_args[1]
            assert 'source_material' in call_kwargs

    def test_generate_sync_error_handling(self, blog_service):
        """测试生成错误处理"""
        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.side_effect = Exception('Generation failed')

            result = blog_service.generate_sync(topic='Test Topic')

            assert result['success'] is False
            assert 'error' in result
            assert 'Generation failed' in result['error']

    def test_generate_async_creates_task(self, blog_service):
        """测试异步生成创建任务"""
        with patch('services.blog_generator.blog_service.get_task_manager') as mock_get_tm:
            mock_task_manager = MagicMock()
            mock_get_tm.return_value = mock_task_manager

            task_id = blog_service.generate_async(
                topic='Test Topic',
                article_type='tutorial'
            )

            # 验证返回了任务 ID
            assert task_id is not None
            assert isinstance(task_id, str)

            # 验证任务被创建
            mock_task_manager.create_task.assert_called_once()

    @pytest.mark.skip(reason="Async generation requires thread mocking")
    def test_generate_async_execution(self, blog_service):
        """测试异步生成执行（需要线程 mock）"""
        pass


class TestBlogServiceCoverGeneration:
    """测试封面生成功能"""

    @pytest.fixture
    def blog_service_with_mocks(self, mock_llm_service, mock_db_service,
                                 mock_image_service, mock_video_service):
        """创建带完整 mock 的 BlogService"""
        from services.blog_generator.blog_service import BlogService

        with patch('services.blog_generator.blog_service.get_image_service',
                   return_value=mock_image_service):
            with patch('services.blog_generator.blog_service.get_video_service',
                       return_value=mock_video_service):
                service = BlogService(
                    llm_service=mock_llm_service,
                    db_service=mock_db_service
                )
                yield service

    def test_generate_cover_image(self, blog_service_with_mocks, mock_image_service):
        """测试生成封面图片"""
        outline = {
            'title': 'Test Blog',
            'sections': [
                {'title': 'Section 1', 'key_points': ['Point 1']},
                {'title': 'Section 2', 'key_points': ['Point 2']}
            ]
        }

        result = blog_service_with_mocks._generate_cover_image(
            outline=outline,
            image_style='minimalist',
            aspect_ratio='16:9'
        )

        # 验证返回了图片 URL
        assert result == 'https://example.com/image.jpg'

        # 验证图片服务被调用
        mock_image_service.generate_image.assert_called_once()

    def test_generate_cover_image_error_handling(self, blog_service_with_mocks,
                                                   mock_image_service):
        """测试封面图片生成错误处理"""
        mock_image_service.generate_image.side_effect = Exception('Image generation failed')

        outline = {'title': 'Test', 'sections': []}

        result = blog_service_with_mocks._generate_cover_image(
            outline=outline,
            image_style='minimalist'
        )

        # 错误时应返回 None
        assert result is None

    @pytest.mark.skip(reason="Video generation requires complex mocking")
    def test_generate_cover_video(self, blog_service_with_mocks):
        """测试生成封面视频（需要复杂 mock）"""
        pass


class TestBlogServiceDatabaseIntegration:
    """测试数据库集成"""

    def test_save_to_database(self, mock_llm_service, mock_db_service):
        """测试保存到数据库"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(
            llm_service=mock_llm_service,
            db_service=mock_db_service
        )

        # Mock 生成结果
        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
                'final_markdown': '# Test Blog',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [{'title': 'S1', 'content': 'C1'}],
                'code_blocks': [{'language': 'python', 'code': 'print()'}],
                'images': [{'url': 'http://example.com/img.jpg'}],
                'review_score': 85
            }

            result = service.generate_sync(
                topic='Test Topic',
                save_to_db=True
            )

            # 验证数据库保存被调用
            mock_db_service.save_history.assert_called_once()

            # 验证保存的数据
            call_kwargs = mock_db_service.save_history.call_args[1]
            assert call_kwargs['topic'] == 'Test Topic'
            assert 'markdown' in call_kwargs
            assert call_kwargs['sections_count'] == 1
            assert call_kwargs['code_blocks_count'] == 1
            assert call_kwargs['images_count'] == 1

    def test_skip_database_save(self, mock_llm_service, mock_db_service):
        """测试跳过数据库保存"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(
            llm_service=mock_llm_service,
            db_service=mock_db_service
        )

        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            result = service.generate_sync(
                topic='Test Topic',
                save_to_db=False
            )

            # 验证数据库保存未被调用
            mock_db_service.save_history.assert_not_called()


class TestBlogServiceConfiguration:
    """测试配置和参数处理"""

    def test_article_type_configuration(self, mock_llm_service, mock_db_service):
        """测试文章类型配置"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(
            llm_service=mock_llm_service,
            db_service=mock_db_service
        )

        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            # 测试不同的文章类型
            for article_type in ['tutorial', 'guide', 'analysis', 'reference']:
                result = service.generate_sync(
                    topic='Test Topic',
                    article_type=article_type
                )

                assert result['success'] is True

                # 验证 article_type 被传递
                call_kwargs = mock_generator.generate.call_args[1]
                assert call_kwargs['article_type'] == article_type

    def test_target_length_configuration(self, mock_llm_service, mock_db_service):
        """测试目标长度配置"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(
            llm_service=mock_llm_service,
            db_service=mock_db_service
        )

        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            # 测试不同的长度
            for length in ['mini', 'short', 'medium', 'long']:
                result = service.generate_sync(
                    topic='Test Topic',
                    target_length=length
                )

                assert result['success'] is True

                # 验证 target_length 被传递
                call_kwargs = mock_generator.generate.call_args[1]
                assert call_kwargs['target_length'] == length

    def test_target_audience_configuration(self, mock_llm_service, mock_db_service):
        """测试目标受众配置"""
        from services.blog_generator.blog_service import BlogService

        service = BlogService(
            llm_service=mock_llm_service,
            db_service=mock_db_service
        )

        with patch('services.blog_generator.blog_service.BlogGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate.return_value = {
                'final_markdown': '# Test',
                'outline': {'title': 'Test', 'sections': []},
                'sections': [],
                'code_blocks': [],
                'images': [],
                'review_score': 80
            }

            # 测试不同的受众
            for audience in ['beginner', 'intermediate', 'advanced', 'expert']:
                result = service.generate_sync(
                    topic='Test Topic',
                    target_audience=audience
                )

                assert result['success'] is True

                # 验证 target_audience 被传递
                call_kwargs = mock_generator.generate.call_args[1]
                assert call_kwargs['target_audience'] == audience
