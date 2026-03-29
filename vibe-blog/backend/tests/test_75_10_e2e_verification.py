"""
75.10 搜索服务集成 — 端到端验证

不 mock init 流程，验证真实初始化 + 搜索路由链路。
确认死代码治理后各服务确实被触发。
"""
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock


class TestE2EServiceInit:
    """E2E: 验证真实 init_blog_services() 流程"""

    def setup_method(self):
        """重置所有全局单例"""
        import services.blog_generator.services.serper_search_service as serper_mod
        serper_mod._serper_service = None
        import services.blog_generator.services.sogou_search_service as sogou_mod
        sogou_mod._sogou_service = None

    @patch.dict('os.environ', {'SERPER_API_KEY': 'test-serper-key'})
    @patch('routes.blog_routes.init_search_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_knowledge_service')
    def test_serper_init_actually_called(
        self, mock_ks, mock_llm, mock_ss, mock_init_ss, caplog
    ):
        """验证 init_serper_service() 真的被执行了（非 mock）"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        with caplog.at_level(logging.INFO):
            from routes.blog_routes import init_blog_services
            init_blog_services({})

        # 验证 Serper 实例真的被创建了
        from services.blog_generator.services.serper_search_service import (
            get_serper_service, SerperSearchService
        )
        serper = get_serper_service()
        assert isinstance(serper, SerperSearchService), \
            f"期望 SerperSearchService 实例，实际是 {type(serper)}"
        assert serper.is_available() is True
        assert serper.api_key == 'test-serper-key'

    @patch.dict('os.environ', {
        'TENCENTCLOUD_SECRET_ID': 'test-secret-id',
        'TENCENTCLOUD_SECRET_KEY': 'test-secret-key',
    })
    @patch('routes.blog_routes.init_search_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_knowledge_service')
    def test_sogou_init_actually_called(
        self, mock_ks, mock_llm, mock_ss, mock_init_ss, caplog
    ):
        """验证 init_sogou_service() 真的被执行了（非 mock）"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        with caplog.at_level(logging.INFO):
            from routes.blog_routes import init_blog_services
            init_blog_services({})

        from services.blog_generator.services.sogou_search_service import (
            get_sogou_service, SogouSearchService
        )
        sogou = get_sogou_service()
        assert isinstance(sogou, SogouSearchService), \
            f"期望 SogouSearchService 实例，实际是 {type(sogou)}"
        assert sogou.is_available() is True


class TestE2ESearchRouting:
    """E2E: 验证 SmartSearchService 路由到 google/sogou 时不再静默失败"""

    def setup_method(self):
        import services.blog_generator.services.serper_search_service as serper_mod
        serper_mod._serper_service = None
        import services.blog_generator.services.sogou_search_service as sogou_mod
        sogou_mod._sogou_service = None

    @patch.dict('os.environ', {'SERPER_API_KEY': 'test-key'})
    @patch('routes.blog_routes.init_search_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_knowledge_service')
    @patch('services.blog_generator.services.serper_search_service.requests.post')
    def test_search_google_reaches_api(
        self, mock_post, mock_ks, mock_llm, mock_ss, mock_init_ss
    ):
        """init 后 _search_google() 真的调用了 Serper API（而非返回 '服务不可用'）"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        # mock Serper HTTP 响应
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "organic": [
                {"title": "Claude Code", "link": "https://example.com", "snippet": "AI coding"}
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        # 直接调用 _search_google
        from services.blog_generator.services.smart_search_service import SmartSearchService
        sss = SmartSearchService.__new__(SmartSearchService)
        result = sss._search_google('Claude Code tutorial', 5)

        # 关键断言：不再返回 "Serper 服务不可用"
        assert result['success'] is True, \
            f"_search_google() 仍然失败: {result.get('error', 'unknown')}"
        assert len(result['results']) > 0
        # 验证 HTTP 请求确实发出了
        mock_post.assert_called_once()

    @patch.dict('os.environ', {
        'TENCENTCLOUD_SECRET_ID': 'test-id',
        'TENCENTCLOUD_SECRET_KEY': 'test-key',
    })
    @patch('routes.blog_routes.init_search_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_knowledge_service')
    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_search_sogou_reaches_api(
        self, mock_post, mock_ks, mock_llm, mock_ss, mock_init_ss
    ):
        """init 后 _search_sogou() 真的调用了腾讯云 API（而非返回 '服务不可用'）"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        # mock 腾讯云 SearchPro 响应
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "Response": {
                "Pages": [
                    {"Title": "AI 测试", "Url": "https://example.com", "Summary": "测试内容"}
                ],
                "TotalCount": 1,
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        from services.blog_generator.services.smart_search_service import SmartSearchService
        sss = SmartSearchService.__new__(SmartSearchService)
        result = sss._search_sogou('AI 大模型', 5)

        assert result['success'] is True, \
            f"_search_sogou() 仍然失败: {result.get('error', 'unknown')}"
        assert len(result['results']) > 0
        mock_post.assert_called_once()


class TestE2EDeadCodeCleanup:
    """E2E: 验证死代码清理无残留"""

    def test_multi_round_searcher_file_deleted(self):
        """D4: multi_round_searcher.py 已删除"""
        path = os.path.join(
            os.path.dirname(__file__), '..',
            'services', 'blog_generator', 'services', 'multi_round_searcher.py'
        )
        assert not os.path.exists(path), \
            f"multi_round_searcher.py 仍然存在: {path}"

    def test_no_import_multi_round_searcher_in_production(self):
        """D4: 生产代码中无 MultiRoundSearcher 引用"""
        import subprocess
        result = subprocess.run(
            ['grep', '-r', 'multi_round_searcher', '--include=*.py',
             '-l', os.path.join(os.path.dirname(__file__), '..', 'services')],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == '', \
            f"生产代码中仍有 multi_round_searcher 引用:\n{result.stdout}"

    def test_init_arxiv_service_removed(self):
        """D5: init_arxiv_service() 函数已删除"""
        from services.blog_generator.services import arxiv_service
        assert not hasattr(arxiv_service, 'init_arxiv_service'), \
            "init_arxiv_service() 函数仍然存在"

    def test_arxiv_lazy_init_still_works(self):
        """D5: get_arxiv_service() lazy-init 正常"""
        # 重置全局变量
        import services.blog_generator.services.arxiv_service as arxiv_mod
        arxiv_mod._arxiv_service = None

        from services.blog_generator.services.arxiv_service import (
            get_arxiv_service, ArxivService
        )
        service = get_arxiv_service()
        assert isinstance(service, ArxivService), \
            f"get_arxiv_service() 返回 {type(service)}，lazy-init 失败"

    def test_knowledge_gap_detector_still_works(self):
        """D4: KnowledgeGapDetector 不受 MultiRoundSearcher 删除影响"""
        from services.blog_generator.services.knowledge_gap_detector import (
            KnowledgeGapDetector
        )
        detector = KnowledgeGapDetector(llm_service=MagicMock())
        assert detector is not None


class TestE2ESourceCuratorRouting:
    """E2E: 验证 SmartSearchService 路由规则正确识别可用源"""

    def setup_method(self):
        import services.blog_generator.services.serper_search_service as serper_mod
        serper_mod._serper_service = None

    @patch.dict('os.environ', {'SERPER_API_KEY': 'test-key'})
    @patch('routes.blog_routes.init_search_service')
    @patch('routes.blog_routes.get_search_service')
    @patch('routes.blog_routes.get_llm_service')
    @patch('routes.blog_routes.get_knowledge_service')
    def test_google_source_in_routing(
        self, mock_ks, mock_llm, mock_ss, mock_init_ss
    ):
        """init 后规则路由能识别 google 为可用源"""
        mock_ss.return_value = MagicMock(is_available=lambda: True)
        mock_llm.return_value = MagicMock(is_available=lambda: False)

        from routes.blog_routes import init_blog_services
        init_blog_services({})

        from services.blog_generator.services.smart_search_service import SmartSearchService
        sss = SmartSearchService.__new__(SmartSearchService)
        sss.search_service = mock_ss.return_value

        routing = sss._rule_based_routing('Claude Code best practices')
        sources = routing.get('sources', [])
        assert 'google' in sources, \
            f"Serper 已初始化但 google 不在路由源中: {sources}"
