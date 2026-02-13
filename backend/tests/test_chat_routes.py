"""
chat_routes 路由测试
测试用例 RT1-RT8: 基础路由测试
"""
import json
import pytest


class TestChatRoutes:
    def test_rt1_create_session(self, chat_client):
        """RT1: POST /session — 创建会话成功 201"""
        resp = chat_client.post('/api/chat/session',
                                json={"topic": "AI 入门指南"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["session_id"].startswith("ws_")
        assert data["topic"] == "AI 入门指南"
        assert data["status"] == "created"

    def test_rt1b_create_session_no_topic(self, chat_client):
        """RT1b: POST /session — 缺少 topic 返回 400"""
        resp = chat_client.post('/api/chat/session', json={})
        assert resp.status_code == 400

    def test_rt2_list_sessions(self, chat_client):
        """RT2: GET /sessions — 列出会话 200"""
        chat_client.post('/api/chat/session', json={"topic": "主题1"})
        chat_client.post('/api/chat/session', json={"topic": "主题2"})
        resp = chat_client.get('/api/chat/sessions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 2

    def test_rt3_get_session(self, chat_client):
        """RT3: GET /session/<id> — 获取会话 200"""
        create_resp = chat_client.post('/api/chat/session',
                                       json={"topic": "测试"})
        sid = create_resp.get_json()["session_id"]
        resp = chat_client.get(f'/api/chat/session/{sid}')
        assert resp.status_code == 200
        assert resp.get_json()["topic"] == "测试"

    def test_rt4_get_session_404(self, chat_client):
        """RT4: GET /session/<bad_id> — 404"""
        resp = chat_client.get('/api/chat/session/ws_nonexistent')
        assert resp.status_code == 404

    def test_rt5_search(self, chat_client):
        """RT5: POST /session/<id>/search — 调研 200"""
        create_resp = chat_client.post('/api/chat/session',
                                       json={"topic": "AI"})
        sid = create_resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/search', json={})
        assert resp.status_code == 200
        assert "search_results" in resp.get_json()

    def test_rt6_outline(self, chat_client):
        """RT6: POST /session/<id>/outline — 生成大纲 200"""
        create_resp = chat_client.post('/api/chat/session',
                                       json={"topic": "AI"})
        sid = create_resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        assert resp.status_code == 200
        assert "outline" in resp.get_json()

    def test_rt7_write(self, chat_client):
        """RT7: POST /session/<id>/write — 写作 200"""
        create_resp = chat_client.post('/api/chat/session',
                                       json={"topic": "AI"})
        sid = create_resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/write',
                                json={"section_id": "s1"})
        assert resp.status_code == 200
        assert "section" in resp.get_json()

    def test_rt8_assemble(self, chat_client):
        """RT8: POST /session/<id>/assemble — 组装 200"""
        create_resp = chat_client.post('/api/chat/session',
                                       json={"topic": "AI"})
        sid = create_resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/assemble', json={})
        assert resp.status_code == 200
        assert "markdown" in resp.get_json()
