"""
75.10 搜索服务集成 — 生命周期测试 (L1 + L2)

验证 init_blog_services() 正确初始化所有搜索服务。
TDD: 修复前应失败（红），修复后应通过（绿）。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock


def _reset_service_globals():
    """重置所有搜索服务的全局单例"""
    import services.blog_generator.services.serper_search_service as serper_mod
    serper_mod._serper_service = None
    import services.blog_generator.services.sogou_search_service as sogou_mod
    sogou_mod._sogou_service = None


class TestServiceLifecycle:
    """L1: 验证 init_blog_services() 正确初始化所有搜索服务"""

    def setup_method(self):
        _reset_service_globals()

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test-key'})
    def test_serper_initialized_after_startup(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """init_blog_services() 后 get_serper_service() 不为 None"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        from services.blog_generator.services.serper_search_service import get_serper_service
        service = get_serper_service()
        assert service is not None, "get_serper_service() 返回 None — init_serper_service() 未被调用"
        assert service.is_available() is True

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    @patch.dict('os.environ', {
        'TENCENTCLOUD_SECRET_ID': 'test-id',
        'TENCENTCLOUD_SECRET_KEY': 'test-key',
    })
    def test_sogou_initialized_after_startup(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """init_blog_services() 后 get_sogou_service() 不为 None"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        from services.blog_generator.services.sogou_search_service import get_sogou_service
        service = get_sogou_service()
        assert service is not None, "get_sogou_service() 返回 None — init_sogou_service() 未被调用"

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    def test_serper_graceful_without_api_key(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """SERPER_API_KEY 未配置时不抛异常"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        # 不应抛异常
        init_blog_services({})

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    def test_sogou_graceful_without_credentials(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """腾讯云凭证未配置时不抛异常"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    def test_zhipu_not_affected_by_optional_init(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """可选服务初始化不影响智谱"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        # 智谱 init 应被调用
        mock_init_ss.assert_called_once()


class TestSearchIntegration:
    """L2: 验证初始化后搜索链路端到端通畅"""

    def setup_method(self):
        _reset_service_globals()

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    @patch.dict('os.environ', {'SERPER_API_KEY': 'test-key'})
    def test_smart_search_google_not_none(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """初始化后 SmartSearchService._search_google() 能拿到 Serper 实例"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        from services.blog_generator.services.serper_search_service import get_serper_service
        serper = get_serper_service()
        assert serper is not None, "SmartSearchService._search_google() 会因 serper=None 返回 success=False"

    @patch('routes.blog_routes.get_knowledge_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.init_search_service')
    @patch.dict('os.environ', {
        'TENCENTCLOUD_SECRET_ID': 'test-id',
        'TENCENTCLOUD_SECRET_KEY': 'test-key',
    })
    def test_smart_search_sogou_not_none(
        self, mock_init_ss, mock_ss, mock_llm, mock_ks
    ):
        """初始化后 SmartSearchService._search_sogou() 能拿到搜狗实例"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        from services.blog_generator.services.sogou_search_service import get_sogou_service
        sogou = get_sogou_service()
        assert sogou is not None, "SmartSearchService._search_sogou() 会因 sogou=None 返回 success=False"
