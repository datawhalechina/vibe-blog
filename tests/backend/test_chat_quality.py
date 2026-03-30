"""
质量检查 API 集成测试
测试用例 CQ1-CQ7: review / factcheck / humanize 端到端测试（Mock Agent 层）
"""
import pytest


class TestQualityIntegration:
    def _create_session_with_section(self, chat_client):
        """创建会话并写入一个章节，返回 session_id"""
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        sid = resp.get_json()["session_id"]
        chat_client.post(f'/api/chat/session/{sid}/write',
                         json={"section_id": "s1"})
        return sid

    def test_cq1_review(self, chat_client):
        """CQ1: 审核 → 返回 review 结果 + 状态变为 reviewing"""
        sid = self._create_session_with_section(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/review', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "review" in data
        # 验证状态更新
        session_resp = chat_client.get(f'/api/chat/session/{sid}')
        assert session_resp.get_json()["status"] == "reviewing"

    def test_cq2_factcheck(self, chat_client):
        """CQ2: 事实核查 → 返回 factcheck 结果"""
        sid = self._create_session_with_section(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/factcheck', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "factcheck" in data

    def test_cq3_humanize_full(self, chat_client):
        """CQ3: 全文去AI味 → 返回 humanized 结果"""
        sid = self._create_session_with_section(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/humanize', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "humanized" in data or "humanized_sections" in data

    def test_cq4_humanize_single_section(self, chat_client):
        """CQ4: 单章节去AI味 → 返回指定章节的 humanized 结果"""
        sid = self._create_session_with_section(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/humanize',
                                json={"section_id": "s1"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "humanized" in data

    def test_cq5_review_nonexistent_session(self, chat_client):
        """CQ5: 审核不存在的会话 → 404"""
        resp = chat_client.post('/api/chat/session/ws_bad/review', json={})
        assert resp.status_code == 404

    def test_cq6_factcheck_nonexistent_session(self, chat_client):
        """CQ6: 事实核查不存在的会话 → 404"""
        resp = chat_client.post('/api/chat/session/ws_bad/factcheck', json={})
        assert resp.status_code == 404

    def test_cq7_full_quality_pipeline(self, chat_client):
        """CQ7: 完整质量检查流程 → review → factcheck → humanize → assemble"""
        sid = self._create_session_with_section(chat_client)
        # review
        r1 = chat_client.post(f'/api/chat/session/{sid}/review', json={})
        assert r1.status_code == 200
        # factcheck
        r2 = chat_client.post(f'/api/chat/session/{sid}/factcheck', json={})
        assert r2.status_code == 200
        # humanize
        r3 = chat_client.post(f'/api/chat/session/{sid}/humanize', json={})
        assert r3.status_code == 200
        # assemble
        r4 = chat_client.post(f'/api/chat/session/{sid}/assemble', json={})
        assert r4.status_code == 200
        assert "markdown" in r4.get_json()
