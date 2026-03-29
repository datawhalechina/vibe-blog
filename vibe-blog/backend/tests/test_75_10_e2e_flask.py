"""
75.10 E2E 验证：真实 Flask App 启动 + 搜索服务初始化

直接调用 create_app()，验证：
1. init_blog_services() 中 Serper/搜狗 init 被调用且不崩溃
2. 搜索服务状态正确（有 Key 的可用，无 Key 的优雅跳过）
3. 通过 Flask test client 触发一次 mini 博客生成
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import pytest


class TestE2EFlaskAppInit:
    """验证真实 Flask App 启动流程"""

    def test_create_app_with_search_init(self, caplog):
        """create_app() 启动不崩溃，搜索服务正确初始化"""
        with caplog.at_level(logging.INFO):
            from app import create_app
            app = create_app()

        # 验证 app 创建成功
        assert app is not None

        # 检查日志中的搜索服务初始化信息
        log_text = caplog.text

        # 智谱搜索应该被初始化（有 ZAI_SEARCH_API_KEY）
        has_zhipu = (
            "智谱搜索服务已初始化" in log_text
            or "智谱搜索服务不可用" in log_text
        )
        assert has_zhipu, f"智谱搜索初始化日志缺失。完整日志:\n{log_text}"

        # Serper 应该有日志（不管是初始化成功还是跳过）
        has_serper_log = (
            "Serper Google 搜索服务已初始化" in log_text
            or "Serper 服务: 未配置 API Key" in log_text
            or "Serper 服务初始化跳过" in log_text
        )
        assert has_serper_log, \
            f"Serper 初始化日志缺失 — init_serper_service() 可能未被调用。完整日志:\n{log_text}"

        # 搜狗应该有日志
        has_sogou_log = (
            "搜狗搜索服务已初始化" in log_text
            or "搜狗搜索: TENCENTCLOUD_SECRET_ID/KEY 未配置" in log_text
            or "搜狗服务初始化跳过" in log_text
        )
        assert has_sogou_log, \
            f"搜狗初始化日志缺失 — init_sogou_service() 可能未被调用。完整日志:\n{log_text}"

        # 博客生成服务应该初始化
        has_blog = "博客生成服务已初始化" in log_text
        # 注意：如果 LLM 服务不可用，博客服务不会初始化，这也是正常的

    def test_search_service_states_after_init(self):
        """验证各搜索服务的运行时状态"""
        from app import create_app
        app = create_app()

        with app.app_context():
            # 智谱
            from services import get_search_service
            zhipu = get_search_service()
            # 有 ZAI_SEARCH_API_KEY 时应该可用
            if os.environ.get('ZAI_SEARCH_API_KEY'):
                assert zhipu is not None, "智谱搜索服务未初始化"

            # Serper — 取决于是否配置了 SERPER_API_KEY
            from services.blog_generator.services.serper_search_service import get_serper_service
            serper = get_serper_service()
            if os.environ.get('SERPER_API_KEY'):
                assert serper is not None and serper.is_available(), \
                    "SERPER_API_KEY 已配置但 Serper 服务不可用"
            else:
                # 无 Key 时，serper 应该被创建但不可用（或为 None）
                if serper is not None:
                    assert not serper.is_available(), \
                        "SERPER_API_KEY 未配置但 Serper 报告可用"

            # 搜狗 — 取决于是否配置了腾讯云凭证
            from services.blog_generator.services.sogou_search_service import get_sogou_service
            sogou = get_sogou_service()
            if os.environ.get('TENCENTCLOUD_SECRET_ID') and os.environ.get('TENCENTCLOUD_SECRET_KEY'):
                assert sogou is not None, "腾讯云凭证已配置但搜狗服务未初始化"
            else:
                assert sogou is None, \
                    "腾讯云凭证未配置但搜狗服务不为 None"

            # ArXiv — lazy-init 应该正常
            from services.blog_generator.services.arxiv_service import get_arxiv_service
            arxiv = get_arxiv_service()
            assert arxiv is not None, "ArXiv lazy-init 失败"


class TestE2EMiniGeneration:
    """通过 Flask test client 触发 mini 博客生成"""

    @pytest.fixture
    def app_and_client(self):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            with app.app_context():
                yield app, client

    def test_mini_generate_endpoint_accepts(self, app_and_client):
        """POST /api/blog/generate 返回 202 + task_id（或 LLM 不可用时 500）"""
        app, client = app_and_client
        resp = client.post('/api/blog/generate', json={
            'topic': 'Claude Code 使用技巧',
            'target_length': 'mini',
            'image_style': 'default',
        })
        if resp.status_code == 500:
            # CI 环境无 LLM API Key，博客生成服务未初始化，500 是预期行为
            data = resp.get_json()
            assert '不可用' in data.get('error', ''), \
                f"500 但错误信息不符合预期: {data}"
            pytest.skip("LLM 服务不可用，跳过生成端点测试")
        assert resp.status_code in (200, 202), \
            f"生成请求失败: {resp.status_code} {resp.get_json()}"
        data = resp.get_json()
        assert data.get('task_id') or data.get('id'), \
            f"响应中没有 task_id: {data}"
