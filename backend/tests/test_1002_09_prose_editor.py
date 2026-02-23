"""
Prose 编辑器 — 单元测试
TDD Red Phase: 先写测试，再实现代码

覆盖:
- ProseEditorAgent 6 种编辑模式路由
- 各模式 user prompt 构建逻辑
- zap 模式 command 注入
- memory_context 注入
- edit_stream 流式接口
- 无效 option 错误处理
- API 路由测试
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── ProseEditorAgent 单元测试 ─────────────────────────────────

class TestProseEditorAgent:
    """ProseEditorAgent 核心逻辑"""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_llm.chat.return_value = "Edited text result"

    def _make_agent(self):
        from services.blog_generator.agents.prose_editor import ProseEditorAgent
        return ProseEditorAgent(self.mock_llm)

    # ── 路由测试 ──

    def test_edit_routes_all_six_modes(self):
        """验证 6 种 option 都能路由到正确的处理方法"""
        agent = self._make_agent()
        for option in ["continue", "improve", "shorter", "longer", "fix", "zap"]:
            self.mock_llm.chat.reset_mock()
            result = agent.edit("Hello world", option=option)
            assert result is not None, f"option={option} 返回 None"
            assert self.mock_llm.chat.called, f"option={option} 未调用 LLM"

    def test_edit_invalid_option_raises(self):
        """验证无效 option 抛出 ValueError"""
        agent = self._make_agent()
        with pytest.raises(ValueError, match="未知编辑模式"):
            agent.edit("Hello", option="invalid")

    # ── User Prompt 构建测试 ──

    def test_continue_sends_raw_content(self):
        """continue 模式直接发送原文（不加前缀）"""
        agent = self._make_agent()
        agent.edit("The weather is sunny", option="continue")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert user_msg["content"] == "The weather is sunny"

    def test_improve_adds_prefix(self):
        """improve 模式添加 'The existing text is:' 前缀"""
        agent = self._make_agent()
        agent.edit("Hello world", option="improve")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "The existing text is:" in user_msg["content"]
        assert "Hello world" in user_msg["content"]

    def test_shorter_adds_prefix(self):
        """shorter 模式添加 'The existing text is:' 前缀"""
        agent = self._make_agent()
        agent.edit("A long paragraph here", option="shorter")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "The existing text is:" in user_msg["content"]

    def test_longer_adds_prefix(self):
        """longer 模式添加 'The existing text is:' 前缀"""
        agent = self._make_agent()
        agent.edit("Short text", option="longer")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "The existing text is:" in user_msg["content"]

    def test_fix_adds_prefix(self):
        """fix 模式添加 'The existing text is:' 前缀"""
        agent = self._make_agent()
        agent.edit("Teh quik brown fox", option="fix")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "The existing text is:" in user_msg["content"]

    def test_zap_includes_command_in_prompt(self):
        """zap 模式将 command 拼入 user prompt"""
        agent = self._make_agent()
        agent.edit("Hello", option="zap", command="make it funnier")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "make it funnier" in user_msg["content"]
        assert "For this text:" in user_msg["content"]
        assert "Hello" in user_msg["content"]

    # ── System Prompt 测试 ──

    def test_edit_sends_system_message(self):
        """验证每次编辑都发送 system prompt"""
        agent = self._make_agent()
        agent.edit("Hello", option="improve")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        system_msg = [m for m in messages if m["role"] == "system"]
        assert len(system_msg) == 1, "应有且仅有 1 条 system message"
        assert len(system_msg[0]["content"]) > 10, "system prompt 不应为空"

    # ── Memory Context 测试 ──

    def test_memory_context_passed_to_prompt(self):
        """验证 memory_context 传入 prompt 模板渲染"""
        agent = self._make_agent()
        agent.edit("Hello", option="improve", memory_context="用户偏好简洁风格")
        messages = self.mock_llm.chat.call_args[1]["messages"]
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "用户偏好简洁风格" in system_msg["content"]

    def test_empty_memory_context_no_error(self):
        """空 memory_context 不报错"""
        agent = self._make_agent()
        result = agent.edit("Hello", option="improve", memory_context="")
        assert result is not None

    # ── 流式接口测试 ──

    def test_edit_stream_returns_iterable(self):
        """edit_stream 返回可迭代对象"""
        agent = self._make_agent()
        self.mock_llm.chat_stream.return_value = "Streamed result"
        result = agent.edit_stream("Hello", option="improve")
        assert hasattr(result, '__iter__') or hasattr(result, '__next__')

    def test_edit_stream_fallback_when_no_chat_stream(self):
        """当 LLM 无 chat_stream 方法时，回退到同步调用"""
        agent = self._make_agent()
        del self.mock_llm.chat_stream  # 移除 chat_stream
        result = agent.edit_stream("Hello", option="improve")
        chunks = list(result)
        assert len(chunks) > 0

    # ── LLM tier 测试 ──

    def test_edit_uses_fast_tier(self):
        """验证编辑使用 fast tier"""
        agent = self._make_agent()
        agent.edit("Hello", option="improve")
        call_kwargs = self.mock_llm.chat.call_args[1]
        assert call_kwargs.get("tier") == "fast" or call_kwargs.get("caller") == "prose_editor"


# ── API 路由测试 ──────────────────────────────────────────────

class TestProseRoutes:
    """Prose 编辑 API 路由"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from flask import Flask
        from routes.prose_routes import prose_bp

        app = Flask(__name__)
        app.register_blueprint(prose_bp)
        app.config['TESTING'] = True
        return app.test_client()

    def test_edit_missing_content_returns_400(self, client):
        """缺少 content 返回 400"""
        resp = client.post('/api/prose/edit', json={"option": "improve"})
        assert resp.status_code == 400

    def test_edit_missing_option_returns_400(self, client):
        """缺少 option 返回 400"""
        resp = client.post('/api/prose/edit', json={"content": "Hello"})
        assert resp.status_code == 400

    def test_edit_invalid_option_returns_400(self, client):
        """无效 option 返回 400"""
        resp = client.post('/api/prose/edit', json={
            "content": "Hello",
            "option": "invalid_mode"
        })
        assert resp.status_code == 400

    @patch('routes.prose_routes.get_llm_service')
    def test_edit_service_unavailable_returns_503(self, mock_get_llm, client):
        """LLM 服务不可用返回 503"""
        mock_get_llm.return_value = None
        resp = client.post('/api/prose/edit', json={
            "content": "Hello",
            "option": "improve"
        })
        assert resp.status_code == 503

    @patch('routes.prose_routes.get_llm_service')
    def test_edit_success_returns_output(self, mock_get_llm, client):
        """成功编辑返回 output"""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.chat.return_value = "Improved text"
        mock_get_llm.return_value = mock_llm

        resp = client.post('/api/prose/edit', json={
            "content": "Hello world",
            "option": "improve"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "output" in data

    @patch('routes.prose_routes.get_llm_service')
    def test_edit_zap_with_command(self, mock_get_llm, client):
        """zap 模式带 command 参数"""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.chat.return_value = "Funnier text"
        mock_get_llm.return_value = mock_llm

        resp = client.post('/api/prose/edit', json={
            "content": "Hello",
            "option": "zap",
            "command": "make it funnier"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    @patch('routes.prose_routes.get_llm_service')
    def test_edit_all_valid_options(self, mock_get_llm, client):
        """所有 6 种有效 option 都返回 200"""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.chat.return_value = "Result"
        mock_get_llm.return_value = mock_llm

        for option in ["continue", "improve", "shorter", "longer", "fix", "zap"]:
            resp = client.post('/api/prose/edit', json={
                "content": "Hello",
                "option": option,
                "command": "test" if option == "zap" else ""
            })
            assert resp.status_code == 200, f"option={option} 返回 {resp.status_code}"
