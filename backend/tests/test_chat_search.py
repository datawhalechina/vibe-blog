"""
搜索/大纲 API 集成测试
测试用例 CS1-CS10: 端到端流程测试（Mock Agent 层）
"""
import pytest


class TestSearchIntegration:
    def test_cs1_search_returns_results(self, chat_client):
        """CS1: 创建会话 → 搜索 → 返回 search_results"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/search', json={})
        assert resp.status_code == 200
        assert "search_results" in resp.get_json()

    def test_cs2_search_updates_session(self, chat_client):
        """CS2: 搜索 → 会话 search_results 已更新"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        chat_client.post(f'/api/chat/session/{sid}/search', json={})
        session_resp = chat_client.get(f'/api/chat/session/{sid}')
        data = session_resp.get_json()
        assert data["status"] == "researching"

    def test_cs3_knowledge_gaps(self, chat_client):
        """CS3: 搜索 → 知识缺口检测 → 返回 gaps"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/knowledge-gaps',
                                json={"content": "一些内容"})
        assert resp.status_code == 200
        assert "knowledge_gaps" in resp.get_json()

    def test_cs4_generate_outline(self, chat_client):
        """CS4: 搜索 → 生成大纲 → 返回 outline"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        assert resp.status_code == 200
        assert "outline" in resp.get_json()

    def test_cs5_outline_updates_session(self, chat_client):
        """CS5: 生成大纲 → 会话 outline 已更新"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        session_resp = chat_client.get(f'/api/chat/session/{sid}')
        data = session_resp.get_json()
        assert data["outline"] is not None
        assert data["status"] == "outlining"

    def test_cs6_edit_outline_title(self, chat_client, chat_app):
        """CS6: 编辑大纲 → 修改标题"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        # 先生成大纲
        chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        # 编辑标题
        resp = chat_client.post(f'/api/chat/session/{sid}/outline/edit',
                                json={"title": "新标题"})
        assert resp.status_code == 200
        assert "outline" in resp.get_json()

    def test_cs7_edit_outline_add_section(self, chat_client):
        """CS7: 编辑大纲 → 添加章节"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        resp = chat_client.post(f'/api/chat/session/{sid}/outline/edit',
                                json={"add_section": {"id": "s4", "title": "新章节"}})
        assert resp.status_code == 200

    def test_cs8_edit_outline_remove_section(self, chat_client):
        """CS8: 编辑大纲 → 删除章节"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        resp = chat_client.post(f'/api/chat/session/{sid}/outline/edit',
                                json={"remove_section_id": "s1"})
        assert resp.status_code == 200

    def test_cs9_outline_without_search(self, chat_client):
        """CS9: 未搜索直接生成大纲 → 仍可成功"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        resp = chat_client.post(f'/api/chat/session/{sid}/outline', json={})
        assert resp.status_code == 200

    def test_cs10_search_nonexistent_session(self, chat_client):
        """CS10: 搜索不存在的会话 → 404"""
        resp = chat_client.post('/api/chat/session/ws_bad/search', json={})
        assert resp.status_code == 404
