"""
搜狗搜索服务（腾讯云 SearchPro API）单元测试
"""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSogouSearchService:
    """搜狗搜索服务测试"""

    def _make_service(self, secret_id='test_id', secret_key='test_key', **kwargs):
        from services.blog_generator.services.sogou_search_service import SogouSearchService
        return SogouSearchService(secret_id=secret_id, secret_key=secret_key, **kwargs)

    def test_is_available_with_keys(self):
        svc = self._make_service()
        assert svc.is_available() is True

    def test_is_available_without_keys(self):
        from services.blog_generator.services.sogou_search_service import SogouSearchService
        svc = SogouSearchService(secret_id='', secret_key='test')
        assert svc.is_available() is False
        svc2 = SogouSearchService(secret_id='test', secret_key='')
        assert svc2.is_available() is False

    def test_search_no_keys(self):
        from services.blog_generator.services.sogou_search_service import SogouSearchService
        svc = SogouSearchService(secret_id='', secret_key='')
        result = svc.search('test')
        assert result['success'] is False
        assert 'API Key 未配置' in result['error']

    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_search_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'Response': {
                'Pages': [
                    json.dumps({
                        'title': 'AI 技术前沿',
                        'url': 'https://example.com/ai',
                        'passage': 'AI 技术最新进展...',
                        'date': '2025-01-15',
                        'site': 'example.com',
                    }),
                    json.dumps({
                        'title': '微信公众号文章',
                        'url': 'https://mp.weixin.qq.com/s/abc123',
                        'passage': '公众号内容...',
                        'date': '2025-01-14',
                        'site': 'mp.weixin.qq.com',
                    }),
                ]
            }
        }
        mock_post.return_value = mock_resp

        svc = self._make_service()
        result = svc.search('AI 技术')

        assert result['success'] is True
        assert len(result['results']) == 2
        # 第一条：普通网页
        assert result['results'][0]['title'] == 'AI 技术前沿'
        assert result['results'][0]['source'] == '搜狗搜索'
        assert result['results'][0]['source_type'] == 'web'
        # 第二条：微信公众号
        assert result['results'][1]['source_type'] == 'wechat'
        assert result['results'][1]['url'] == 'https://mp.weixin.qq.com/s/abc123'

    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_wechat_source_detection(self, mock_post):
        """微信公众号来源标记"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'Response': {
                'Pages': [
                    json.dumps({
                        'title': '公众号文章',
                        'url': 'https://mp.weixin.qq.com/s/xyz',
                        'passage': '内容',
                        'date': '2025-01-01',
                        'site': 'mp.weixin.qq.com',
                    }),
                ]
            }
        }
        mock_post.return_value = mock_resp

        svc = self._make_service()
        result = svc.search('test')
        assert result['results'][0]['source_type'] == 'wechat'

    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_search_api_error(self, mock_post):
        """API 返回错误"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'Response': {
                'Error': {
                    'Code': 'AuthFailure',
                    'Message': '认证失败',
                }
            }
        }
        mock_post.return_value = mock_resp

        svc = self._make_service()
        result = svc.search('test')
        assert result['success'] is False
        assert '认证失败' in result['error']

    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_search_http_error(self, mock_post):
        """HTTP 请求失败 + 重试"""
        mock_post.side_effect = Exception('Connection refused')

        svc = self._make_service()
        result = svc.search('test')
        assert result['success'] is False
        # 应该重试了 3 次
        assert mock_post.call_count == 3

    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_search_retry_then_success(self, mock_post):
        """第一次失败，第二次成功"""
        fail_resp = MagicMock()
        fail_resp.status_code = 500

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {
            'Response': {
                'Pages': [
                    json.dumps({
                        'title': 'OK',
                        'url': 'https://example.com',
                        'passage': 'content',
                        'date': '2025-01-01',
                        'site': 'example.com',
                    }),
                ]
            }
        }
        mock_post.side_effect = [Exception('timeout'), ok_resp]

        svc = self._make_service()
        result = svc.search('test')
        assert result['success'] is True
        assert len(result['results']) == 1
        assert mock_post.call_count == 2

    @patch('services.blog_generator.services.sogou_search_service.requests.post')
    def test_empty_pages(self, mock_post):
        """空结果"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'Response': {
                'Pages': []
            }
        }
        mock_post.return_value = mock_resp

        svc = self._make_service()
        result = svc.search('test')
        assert result['success'] is True
        assert len(result['results']) == 0

    def test_generate_summary(self):
        svc = self._make_service()
        results = [
            {'title': 'A', 'content': 'Content A', 'source': '搜狗搜索'},
            {'title': 'B', 'content': 'Content B', 'source': '搜狗搜索'},
        ]
        summary = svc._generate_summary(results)
        assert 'A' in summary
        assert 'B' in summary

    def test_init_and_get_service(self):
        from services.blog_generator.services.sogou_search_service import (
            init_sogou_service, get_sogou_service
        )
        with patch.dict(os.environ, {
            'TENCENTCLOUD_SECRET_ID': 'test_id',
            'TENCENTCLOUD_SECRET_KEY': 'test_key',
        }):
            svc = init_sogou_service()
            assert svc is not None
            assert svc.is_available() is True
            assert get_sogou_service() is svc

    def test_init_service_no_keys(self):
        from services.blog_generator.services.sogou_search_service import (
            init_sogou_service, get_sogou_service, _sogou_service
        )
        import services.blog_generator.services.sogou_search_service as mod
        with patch.dict(os.environ, {}, clear=True):
            # 清除可能存在的环境变量
            os.environ.pop('TENCENTCLOUD_SECRET_ID', None)
            os.environ.pop('TENCENTCLOUD_SECRET_KEY', None)
            svc = init_sogou_service()
            assert svc is None
            assert get_sogou_service() is None
