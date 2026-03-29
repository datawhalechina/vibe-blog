"""
101.113 多轮对话 LangGraph interrupt 改造 - API 路由测试

测试覆盖：
1. POST /api/tasks/<task_id>/resume 正常流程
2. POST /api/tasks/<task_id>/resume 参数校验
3. POST /api/tasks/<task_id>/confirm-outline 兼容性
4. 任务不存在时返回 404
"""

import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    """创建 Flask 测试应用"""
    import sys
    import os
    # 确保 backend 在 sys.path 中
    backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
    if backend_dir not in sys.path:
        sys.path.insert(0, os.path.abspath(backend_dir))

    from flask import Flask
    from routes.blog_routes import blog_bp

    app = Flask(__name__)
    app.register_blueprint(blog_bp)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestResumeTaskRoute:
    """测试 /api/tasks/<task_id>/resume 路由"""

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_accept_success(self, mock_get_svc, client):
        """accept 操作应返回成功"""
        mock_svc = MagicMock()
        mock_svc.resume_generation.return_value = True
        mock_get_svc.return_value = mock_svc

        resp = client.post(
            '/api/tasks/task-123/resume',
            data=json.dumps({'action': 'accept'}),
            content_type='application/json'
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        mock_svc.resume_generation.assert_called_once_with(
            'task-123', action='accept', outline=None
        )

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_edit_success(self, mock_get_svc, client):
        """edit 操作应传递 outline"""
        mock_svc = MagicMock()
        mock_svc.resume_generation.return_value = True
        mock_get_svc.return_value = mock_svc

        edited_outline = {'title': '新大纲', 'sections': []}
        resp = client.post(
            '/api/tasks/task-123/resume',
            data=json.dumps({'action': 'edit', 'outline': edited_outline}),
            content_type='application/json'
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        mock_svc.resume_generation.assert_called_once_with(
            'task-123', action='edit', outline=edited_outline
        )

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_invalid_action(self, mock_get_svc, client):
        """无效的 action 应返回 400"""
        resp = client.post(
            '/api/tasks/task-123/resume',
            data=json.dumps({'action': 'invalid'}),
            content_type='application/json'
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_edit_without_outline(self, mock_get_svc, client):
        """edit 操作缺少 outline 应返回 400"""
        resp = client.post(
            '/api/tasks/task-123/resume',
            data=json.dumps({'action': 'edit'}),
            content_type='application/json'
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_task_not_found(self, mock_get_svc, client):
        """任务不存在应返回 404"""
        mock_svc = MagicMock()
        mock_svc.resume_generation.return_value = False
        mock_get_svc.return_value = mock_svc

        resp = client.post(
            '/api/tasks/unknown/resume',
            data=json.dumps({'action': 'accept'}),
            content_type='application/json'
        )

        assert resp.status_code == 404

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_service_unavailable(self, mock_get_svc, client):
        """服务不可用应返回 500"""
        mock_get_svc.return_value = None

        resp = client.post(
            '/api/tasks/task-123/resume',
            data=json.dumps({'action': 'accept'}),
            content_type='application/json'
        )

        assert resp.status_code == 500

    @patch('routes.blog_routes.get_blog_service')
    def test_resume_default_action(self, mock_get_svc, client):
        """不传 action 应默认为 accept"""
        mock_svc = MagicMock()
        mock_svc.resume_generation.return_value = True
        mock_get_svc.return_value = mock_svc

        resp = client.post(
            '/api/tasks/task-123/resume',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert resp.status_code == 200
        mock_svc.resume_generation.assert_called_once_with(
            'task-123', action='accept', outline=None
        )


class TestConfirmOutlineCompatibility:
    """测试 /api/tasks/<task_id>/confirm-outline 兼容性"""

    @patch('routes.blog_routes.get_blog_service')
    def test_confirm_outline_delegates_to_resume(self, mock_get_svc, client):
        """confirm-outline 应转发到 resume 逻辑"""
        mock_svc = MagicMock()
        mock_svc.resume_generation.return_value = True
        mock_get_svc.return_value = mock_svc

        resp = client.post(
            '/api/tasks/task-123/confirm-outline',
            data=json.dumps({'action': 'accept'}),
            content_type='application/json'
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        mock_svc.resume_generation.assert_called_once()

    @patch('routes.blog_routes.get_blog_service')
    def test_confirm_outline_edit_with_outline(self, mock_get_svc, client):
        """confirm-outline edit 操作应正确传递 outline"""
        mock_svc = MagicMock()
        mock_svc.resume_generation.return_value = True
        mock_get_svc.return_value = mock_svc

        outline = {'title': '编辑后', 'sections': [{'title': 'S1'}]}
        resp = client.post(
            '/api/tasks/task-456/confirm-outline',
            data=json.dumps({'action': 'edit', 'outline': outline}),
            content_type='application/json'
        )

        assert resp.status_code == 200
        mock_svc.resume_generation.assert_called_once_with(
            'task-456', action='edit', outline=outline
        )
