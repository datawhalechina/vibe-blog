"""
写作/编辑 API 集成测试
测试用例 CW1-CW11: 写作流程端到端测试（Mock Agent 层）
"""
import pytest


class TestWriteIntegration:
    def _create_session(self, chat_client):
        resp = chat_client.post('/api/chat/session', json={"topic": "AI"})
        return resp.get_json()["session_id"]

    def test_cw1_write_section(self, chat_client):
        """CW1: 写作第一个章节 → 返回 section content"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/write',
                                json={"section_id": "s1"})
        assert resp.status_code == 200
        assert "section" in resp.get_json()

    def test_cw2_write_updates_session(self, chat_client):
        """CW2: 写作 → 会话 sections 已更新"""
        sid = self._create_session(chat_client)
        chat_client.post(f'/api/chat/session/{sid}/write',
                         json={"section_id": "s1"})
        session_resp = chat_client.get(f'/api/chat/session/{sid}')
        data = session_resp.get_json()
        assert data["status"] == "writing"
        assert len(data["sections"]) >= 1

    def test_cw3_write_multiple_sections(self, chat_client):
        """CW3: 写作多个章节 → sections 列表增长"""
        sid = self._create_session(chat_client)
        chat_client.post(f'/api/chat/session/{sid}/write',
                         json={"section_id": "s1"})
        chat_client.post(f'/api/chat/session/{sid}/write',
                         json={"section_id": "s2"})
        session_resp = chat_client.get(f'/api/chat/session/{sid}')
        assert len(session_resp.get_json()["sections"]) >= 2

    def test_cw4_edit_section(self, chat_client):
        """CW4: 编辑章节 → 返回修改后内容"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/edit',
                                json={"section_id": "s1",
                                      "instructions": "增加示例"})
        assert resp.status_code == 200
        assert "content" in resp.get_json()

    def test_cw5_enhance_section(self, chat_client):
        """CW5: 增强章节 → 返回增强后内容"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/enhance',
                                json={"section_id": "s1"})
        assert resp.status_code == 200
        assert "content" in resp.get_json()

    def test_cw6_generate_code(self, chat_client):
        """CW6: 生成代码 → 返回 code block"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/code',
                                json={"description": "打印 hello",
                                      "language": "python"})
        assert resp.status_code == 200
        assert "code_block" in resp.get_json()

    def test_cw7_generate_image(self, chat_client):
        """CW7: 生成配图 → 返回 image info"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/image',
                                json={"description": "AI 架构图"})
        assert resp.status_code == 200
        assert "image" in resp.get_json()

    def test_cw8_write_no_section_id(self, chat_client):
        """CW8: 写作缺少 section_id → 400"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/write', json={})
        assert resp.status_code == 400

    def test_cw9_review(self, chat_client):
        """CW9: 审核 → 返回 review 结果"""
        sid = self._create_session(chat_client)
        resp = chat_client.post(f'/api/chat/session/{sid}/review', json={})
        assert resp.status_code == 200
        assert "review" in resp.get_json()

    def test_cw10_write_updates_status(self, chat_client):
        """CW10: 写作 → 状态变为 writing"""
        sid = self._create_session(chat_client)
        chat_client.post(f'/api/chat/session/{sid}/write',
                         json={"section_id": "s1"})
        session_resp = chat_client.get(f'/api/chat/session/{sid}')
        assert session_resp.get_json()["status"] == "writing"

    def test_cw11_full_flow_to_assemble(self, chat_client):
        """CW11: 全部章节写完 → 可以组装"""
        sid = self._create_session(chat_client)
        chat_client.post(f'/api/chat/session/{sid}/write',
                         json={"section_id": "s1"})
        resp = chat_client.post(f'/api/chat/session/{sid}/assemble', json={})
        assert resp.status_code == 200
        assert "markdown" in resp.get_json()
