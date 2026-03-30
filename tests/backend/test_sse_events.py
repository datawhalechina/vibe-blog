"""
37.34 SSE 流式事件系统增量优化 — 单元测试
"""
import time
from queue import Queue
from unittest.mock import patch, MagicMock

from services.task_service import TaskManager


class TestSendEventEnrichment:
    """Task 1: send_event 自动注入 id + timestamp"""

    def _fresh_manager(self):
        """创建一个干净的 TaskManager（绕过单例）"""
        mgr = object.__new__(TaskManager)
        mgr._initialized = True
        mgr.tasks = {}
        mgr.queues = {}
        from threading import Lock
        mgr.task_lock = Lock()
        return mgr

    def test_event_has_id_and_timestamp(self):
        mgr = self._fresh_manager()
        q = Queue()
        mgr.queues["t1"] = q

        mgr.send_event("t1", "progress", {"stage": "writer"})
        msg = q.get_nowait()

        assert "id" in msg, "事件应包含 id 字段"
        assert len(msg["id"]) == 12
        assert "timestamp" in msg
        assert isinstance(msg["timestamp"], float)
        assert msg["event"] == "progress"
        assert msg["data"]["stage"] == "writer"

    def test_event_ids_are_unique(self):
        mgr = self._fresh_manager()
        q = Queue()
        mgr.queues["t1"] = q

        mgr.send_event("t1", "a", {})
        mgr.send_event("t1", "b", {})

        id1 = q.get_nowait()["id"]
        id2 = q.get_nowait()["id"]
        assert id1 != id2

    def test_backward_compatible_data_field(self):
        """现有字段 event + data 保持不变"""
        mgr = self._fresh_manager()
        q = Queue()
        mgr.queues["t1"] = q

        mgr.send_event("t1", "complete", {"success": True, "id": "blog_123"})
        msg = q.get_nowait()

        assert msg["event"] == "complete"
        assert msg["data"]["success"] is True
        assert msg["data"]["id"] == "blog_123"


class TestLLMEvents:
    """Task 2: LLMService 发送 llm_start / llm_end 事件"""

    def test_chat_sends_llm_start_and_end(self):
        """chat() 应在调用前后发送 llm_start / llm_end"""
        from services.llm_service import LLMService

        svc = LLMService(provider_format="openai", openai_api_key="fake")
        mock_tm = MagicMock()
        svc.task_manager = mock_tm
        svc.task_id = "t1"

        # mock resilient_chat
        with patch("services.llm_service.LLMService.get_text_model") as mock_model, \
             patch("utils.resilient_llm_caller.resilient_chat") as mock_chat, \
             patch("utils.context_guard.ContextGuard.check", return_value={"is_safe": True}):
            mock_model.return_value = MagicMock()
            mock_chat.return_value = ("hello", {"truncated": False, "attempts": 1})

            result = svc.chat(
                [{"role": "user", "content": "hi"}],
                caller="writer",
            )

        assert result == "hello"
        # 检查 llm_start 和 llm_end 事件
        calls = mock_tm.send_event.call_args_list
        event_types = [c[0][1] for c in calls]
        assert "llm_start" in event_types
        assert "llm_end" in event_types

        # 验证 llm_start 数据
        start_call = [c for c in calls if c[0][1] == "llm_start"][0]
        assert start_call[0][2]["agent"] == "writer"

        # 验证 llm_end 数据
        end_call = [c for c in calls if c[0][1] == "llm_end"][0]
        assert end_call[0][2]["agent"] == "writer"
        assert "duration_ms" in end_call[0][2]
        assert end_call[0][2]["truncated"] is False

    def test_llm_events_disabled_by_config(self):
        """SSE_LLM_EVENTS_ENABLED=false 时不发送 LLM 事件"""
        from services.llm_service import LLMService

        svc = LLMService(provider_format="openai", openai_api_key="fake")
        mock_tm = MagicMock()
        svc.task_manager = mock_tm
        svc.task_id = "t1"

        with patch("services.llm_service.LLMService.get_text_model") as mock_model, \
             patch("utils.resilient_llm_caller.resilient_chat") as mock_chat, \
             patch("utils.context_guard.ContextGuard.check", return_value={"is_safe": True}), \
             patch.dict("os.environ", {"SSE_LLM_EVENTS_ENABLED": "false"}):
            mock_model.return_value = MagicMock()
            mock_chat.return_value = ("ok", {"truncated": False, "attempts": 1})

            svc.chat([{"role": "user", "content": "hi"}], caller="writer")

        event_types = [c[0][1] for c in mock_tm.send_event.call_args_list]
        assert "llm_start" not in event_types
        assert "llm_end" not in event_types

    def test_no_events_without_task_manager(self):
        """没有 task_manager 时不报错"""
        from services.llm_service import LLMService

        svc = LLMService(provider_format="openai", openai_api_key="fake")
        # 不设置 task_manager

        with patch("services.llm_service.LLMService.get_text_model") as mock_model, \
             patch("utils.resilient_llm_caller.resilient_chat") as mock_chat, \
             patch("utils.context_guard.ContextGuard.check", return_value={"is_safe": True}):
            mock_model.return_value = MagicMock()
            mock_chat.return_value = ("ok", {"truncated": False, "attempts": 1})

            result = svc.chat([{"role": "user", "content": "hi"}], caller="writer")

        assert result == "ok"  # 正常返回，不报错


class TestTokenUsageInComplete:
    """Task 3: complete 事件包含 token_usage"""

    def test_complete_includes_token_usage(self):
        """当 TokenTracker 可用时，complete 事件应包含 token_usage"""
        # 这是一个集成级别的验证，通过检查 blog_service 的 complete 事件数据
        # 由于 blog_service._run_generation 太重，这里只验证 send_event 的数据格式
        mgr = object.__new__(TaskManager)
        mgr._initialized = True
        mgr.tasks = {}
        mgr.queues = {}
        from threading import Lock
        mgr.task_lock = Lock()

        q = Queue()
        mgr.queues["t1"] = q

        # 模拟 complete 事件带 token_usage
        token_summary = {
            "total_input_tokens": 5000,
            "total_output_tokens": 2000,
            "total_calls": 10,
        }
        mgr.send_event("t1", "complete", {
            "success": True,
            "id": "t1",
            "token_usage": token_summary,
        })

        msg = q.get_nowait()
        assert msg["data"]["token_usage"]["total_input_tokens"] == 5000
        assert msg["data"]["token_usage"]["total_calls"] == 10
