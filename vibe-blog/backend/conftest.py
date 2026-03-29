"""
Shared pytest fixtures for VibeBlog backend tests.
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock
from typing import Generator

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)


# ============ Flask App Fixtures ============

@pytest.fixture
def app(monkeypatch):
    """Create Flask app for testing."""
    # Mock all services before importing app
    from unittest.mock import MagicMock

    # Mock service getters
    mock_blog_svc = MagicMock()
    mock_db_svc = MagicMock()
    mock_task_mgr = MagicMock()
    mock_file_parser = MagicMock()

    monkeypatch.setattr('routes.blog_routes.get_blog_service', lambda: mock_blog_svc)
    monkeypatch.setattr('routes.blog_routes.get_db_service', lambda: mock_db_svc)
    monkeypatch.setattr('routes.blog_routes.get_file_parser', lambda: mock_file_parser)
    monkeypatch.setattr('routes.history_routes.get_db_service', lambda: mock_db_svc)
    monkeypatch.setattr('routes.task_routes.get_task_manager', lambda: mock_task_mgr)
    monkeypatch.setattr('routes.static_routes.get_db_service', lambda: mock_db_svc)
    monkeypatch.setattr('routes.book_routes.get_db_service', lambda: mock_db_svc)

    from app import create_app
    flask_app = create_app()
    flask_app.config.update({
        'TESTING': True,
        'DEBUG': False,
    })

    # Store mocks on app for access in tests
    flask_app.mock_blog_service = mock_blog_svc
    flask_app.mock_db_service = mock_db_svc
    flask_app.mock_task_manager = mock_task_mgr
    flask_app.mock_file_parser = mock_file_parser

    yield flask_app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create Flask CLI test runner."""
    return app.test_cli_runner()


# ============ Database Fixtures ============

@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = MagicMock()
    db.cursor.return_value = MagicMock()
    return db


@pytest.fixture
def sample_blog_data():
    """Sample blog data for testing."""
    return {
        'id': 'test-blog-123',
        'title': 'Test Blog Title',
        'content': '# Test Content\n\nThis is a test blog.',
        'cover_image': 'https://example.com/cover.jpg',
        'cover_video': 'https://example.com/cover.mp4',
        'word_count': 1500,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
    }


# ============ LLM Service Fixtures ============

@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    return {
        'content': 'This is a generated blog post about AI.',
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 200,
            'total_tokens': 300,
        },
    }


@pytest.fixture
def mock_llm_service(mock_llm_response):
    """Mock LLM service."""
    service = MagicMock()
    service.generate.return_value = mock_llm_response['content']
    service.generate_async.return_value = mock_llm_response['content']
    return service


# ============ Image/Video Service Fixtures ============

@pytest.fixture
def mock_image_service():
    """Mock image generation service."""
    service = MagicMock()
    service.generate_image.return_value = 'https://example.com/generated-image.jpg'
    service.generate_images.return_value = [
        'https://example.com/image1.jpg',
        'https://example.com/image2.jpg',
    ]
    return service


@pytest.fixture
def mock_video_service():
    """Mock video generation service."""
    service = MagicMock()
    service.generate_video.return_value = 'https://example.com/generated-video.mp4'
    return service


# ============ OSS Service Fixtures ============

@pytest.fixture
def mock_oss_service():
    """Mock OSS upload service."""
    service = MagicMock()
    service.upload_file.return_value = 'https://oss.example.com/uploaded-file.jpg'
    service.upload_bytes.return_value = 'https://oss.example.com/uploaded-bytes.jpg'
    return service


# ============ Blog Generator Fixtures ============

@pytest.fixture
def mock_blog_generator(mock_llm_service, mock_image_service, mock_video_service):
    """Mock blog generator."""
    generator = MagicMock()
    generator.generate.return_value = {
        'title': 'Generated Blog Title',
        'content': '# Generated Content\n\nThis is generated.',
        'cover_image': 'https://example.com/cover.jpg',
        'cover_video': 'https://example.com/cover.mp4',
    }
    return generator


# ============ Environment Fixtures ============

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    env_vars = {
        'OPENAI_API_KEY': 'test-openai-key',
        'GOOGLE_API_KEY': 'test-google-key',
        'OSS_ACCESS_KEY_ID': 'test-oss-key',
        'OSS_ACCESS_KEY_SECRET': 'test-oss-secret',
        'OSS_BUCKET_NAME': 'test-bucket',
        'OSS_ENDPOINT': 'https://oss.example.com',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


# ============ Cleanup Fixtures ============

@pytest.fixture
def mock_blog_service(app):
    """Get mock blog service from app."""
    return app.mock_blog_service


@pytest.fixture
def mock_db_service(app):
    """Get mock database service from app."""
    return app.mock_db_service


@pytest.fixture
def mock_task_manager(app):
    """Get mock task manager from app."""
    return app.mock_task_manager


@pytest.fixture
def mock_file_parser(app):
    """Get mock file parser from app."""
    return app.mock_file_parser


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test."""
    yield
    # Cleanup happens automatically with pytest-mock


# ============ Chat Fixtures ============

@pytest.fixture
def chat_session_mgr():
    """In-memory WritingSessionManager for chat testing."""
    from services.chat.writing_session import WritingSessionManager
    return WritingSessionManager(db_path=":memory:")


@pytest.fixture
def chat_session_id(chat_session_mgr):
    """Create a test session and return its ID."""
    session = chat_session_mgr.create(topic="测试主题：AI 入门指南")
    return session.session_id


@pytest.fixture
def sample_outline():
    """Sample outline for testing."""
    return {
        "title": "AI 入门指南",
        "sections": [
            {"id": "s1", "title": "什么是 AI", "key_points": ["定义", "历史"]},
            {"id": "s2", "title": "机器学习基础", "key_points": ["监督学习", "无监督学习"]},
            {"id": "s3", "title": "深度学习", "key_points": ["神经网络", "CNN", "RNN"]},
        ]
    }


@pytest.fixture
def mock_dispatcher():
    """Mock AgentDispatcher with all methods mocked."""
    dispatcher = MagicMock()
    dispatcher.search.return_value = {"search_results": [{"title": "result"}]}
    dispatcher.detect_knowledge_gaps.return_value = {"knowledge_gaps": []}
    dispatcher.generate_outline.return_value = {
        "outline": {"title": "AI 指南", "sections": [{"id": "s1", "title": "简介"}]}
    }
    dispatcher.edit_outline.return_value = {
        "outline": {"title": "新标题", "sections": []}
    }
    dispatcher.write_section.return_value = {
        "section": {"id": "s1", "title": "简介", "content": "这是简介内容"}
    }
    dispatcher.edit_section.return_value = {"content": "编辑后的内容"}
    dispatcher.enhance_section.return_value = {"content": "增强后的内容"}
    dispatcher.generate_code.return_value = {"code_block": {"code": "print('hi')"}}
    dispatcher.generate_image.return_value = {"image": {"url": "http://img.png"}}
    dispatcher.review.return_value = {"review": {"score": 85}}
    dispatcher.factcheck.return_value = {"factcheck": {"score": 90}}
    dispatcher.humanize.return_value = {"humanized": {"rewritten": "自然内容"}}
    dispatcher.assemble.return_value = {"markdown": {"final_markdown": "# AI\n..."}}
    dispatcher.get_preview.return_value = {"preview": "# AI\n...", "section_count": 1}
    return dispatcher


@pytest.fixture
def chat_app(monkeypatch, mock_dispatcher, chat_session_mgr):
    """Flask app with chat services initialized."""
    monkeypatch.setattr('routes.blog_routes.get_blog_service', lambda: MagicMock())
    monkeypatch.setattr('routes.blog_routes.get_db_service', lambda: MagicMock())
    monkeypatch.setattr('routes.blog_routes.get_file_parser', lambda: MagicMock())
    monkeypatch.setattr('routes.history_routes.get_db_service', lambda: MagicMock())
    monkeypatch.setattr('routes.task_routes.get_task_manager', lambda: MagicMock())
    monkeypatch.setattr('routes.static_routes.get_db_service', lambda: MagicMock())
    monkeypatch.setattr('routes.book_routes.get_db_service', lambda: MagicMock())

    from app import create_app
    from routes.chat_routes import init_chat_service

    flask_app = create_app()
    flask_app.config.update({'TESTING': True, 'DEBUG': False})

    init_chat_service(chat_session_mgr, mock_dispatcher)

    flask_app.mock_dispatcher = mock_dispatcher
    flask_app.chat_session_mgr = chat_session_mgr

    yield flask_app


@pytest.fixture
def chat_client(chat_app):
    """Flask test client for chat API."""
    return chat_app.test_client()
