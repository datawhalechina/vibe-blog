"""
37.09 统一 ToolManager — 单元测试
"""
import time
from unittest.mock import MagicMock

from utils.tool_manager import BlogToolManager, ToolDefinition


# ============ ToolDefinition 测试 ============

class TestToolDefinition:
    def test_defaults(self):
        td = ToolDefinition(name="t", func=lambda: None, description="desc")
        assert td.name == "t"
        assert td.timeout == 300
        assert td.metadata == {}

    def test_custom_timeout(self):
        td = ToolDefinition(name="t", func=lambda: None, description="d", timeout=60)
        assert td.timeout == 60


# ============ 注册与发现 ============

class TestRegisterAndDiscover:
    def test_register_and_get_all(self):
        mgr = BlogToolManager()
        mgr.register("search", lambda q: q, description="搜索")
        mgr.register("image", lambda p: p, description="图片")

        tools = mgr.get_all_tools()
        names = [t["name"] for t in tools]
        assert "search" in names
        assert "image" in names
        assert len(tools) == 2

    def test_register_decorator(self):
        mgr = BlogToolManager()

        @mgr.register_decorator("my_tool", description="装饰器注册")
        def my_func(x):
            return x * 2

        assert "my_tool" in [t["name"] for t in mgr.get_all_tools()]
        # 原函数仍可直接调用
        assert my_func(3) == 6

    def test_get_all_tools_excludes_blacklist(self):
        mgr = BlogToolManager(blacklist={"blocked"})
        mgr.register("ok", lambda: None, description="ok")
        mgr.register("blocked", lambda: None, description="blocked")

        names = [t["name"] for t in mgr.get_all_tools()]
        assert "ok" in names
        assert "blocked" not in names


# ============ 黑名单 ============

class TestBlacklist:
    def test_blacklist_from_init(self):
        mgr = BlogToolManager(blacklist={"a", "b"})
        mgr.register("a", lambda: None, description="a")
        mgr.register("c", lambda: None, description="c")

        names = [t["name"] for t in mgr.get_all_tools()]
        assert "a" not in names
        assert "c" in names

    def test_execute_blocked_tool(self):
        mgr = BlogToolManager(blacklist={"blocked"})
        mgr.register("blocked", lambda: "hi", description="blocked")

        result = mgr.execute_tool("blocked")
        assert result["success"] is False
        assert "blocked" in result["error"].lower() or "blacklist" in result["error"].lower()


# ============ execute_tool ============

class TestExecuteTool:
    def test_normal_execution(self):
        mgr = BlogToolManager()
        mgr.register("add", lambda a, b: a + b, description="加法")

        result = mgr.execute_tool("add", a=1, b=2)
        assert result["success"] is True
        assert result["result"] == 3
        assert result["duration_ms"] >= 0

    def test_unknown_tool(self):
        mgr = BlogToolManager()
        result = mgr.execute_tool("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"].lower() or "unknown" in result["error"].lower()

    def test_exception_handling(self):
        def bad_func():
            raise ValueError("boom")

        mgr = BlogToolManager()
        mgr.register("bad", bad_func, description="会报错")

        result = mgr.execute_tool("bad")
        assert result["success"] is False
        assert "boom" in result["error"]

    def test_timeout_protection(self):
        def slow_func():
            time.sleep(5)
            return "done"

        mgr = BlogToolManager()
        mgr.register("slow", slow_func, description="慢函数", timeout=1)

        result = mgr.execute_tool("slow")
        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    def test_result_dict_passthrough(self):
        """工具返回 dict 时直接透传"""
        mgr = BlogToolManager()
        mgr.register("dict_tool", lambda: {"key": "val"}, description="返回dict")

        result = mgr.execute_tool("dict_tool")
        assert result["success"] is True
        assert result["result"] == {"key": "val"}


# ============ 日志集成 ============

class TestTaskLogIntegration:
    def test_log_step_on_execute(self):
        mock_log = MagicMock()
        mgr = BlogToolManager(task_log=mock_log)
        mgr.register("t", lambda: "ok", description="test")

        mgr.execute_tool("t")
        mock_log.log_step.assert_called_once()
        call_kwargs = mock_log.log_step.call_args
        assert call_kwargs[0][0] == "tool_manager"  # agent
        assert call_kwargs[0][1] == "t"  # action = tool name

    def test_set_task_log(self):
        mgr = BlogToolManager()
        mgr.register("t", lambda: "ok", description="test")

        mock_log = MagicMock()
        mgr.set_task_log(mock_log)
        mgr.execute_tool("t")
        mock_log.log_step.assert_called_once()

    def test_log_step_on_error(self):
        mock_log = MagicMock()
        mgr = BlogToolManager(task_log=mock_log)
        mgr.register("bad", lambda: 1/0, description="error")

        mgr.execute_tool("bad")
        call_kwargs = mock_log.log_step.call_args
        assert "error" in str(call_kwargs).lower() or call_kwargs[1].get("level") == "error"


# ============ 执行统计 ============

class TestExecutionStats:
    def test_stats_after_executions(self):
        mgr = BlogToolManager()
        mgr.register("t", lambda: "ok", description="test")

        mgr.execute_tool("t")
        mgr.execute_tool("t")

        stats = mgr.get_execution_stats()
        assert stats["t"]["calls"] == 2
        assert stats["t"]["successes"] == 2
        assert stats["t"]["failures"] == 0

    def test_stats_with_failure(self):
        mgr = BlogToolManager()
        mgr.register("bad", lambda: 1/0, description="error")

        mgr.execute_tool("bad")

        stats = mgr.get_execution_stats()
        assert stats["bad"]["failures"] == 1


# ============ 参数自动修复 ============

class TestFixArguments:
    def test_fix_known_alias(self):
        mgr = BlogToolManager()
        fixed = mgr.fix_arguments("web_search", {"q": "AI"})
        assert fixed == {"query": "AI"}

    def test_no_fix_when_correct(self):
        mgr = BlogToolManager()
        fixed = mgr.fix_arguments("web_search", {"query": "AI"})
        assert fixed == {"query": "AI"}

    def test_no_fix_for_unknown_tool(self):
        mgr = BlogToolManager()
        fixed = mgr.fix_arguments("unknown_tool", {"q": "AI"})
        assert fixed == {"q": "AI"}

    def test_fix_deep_scrape(self):
        mgr = BlogToolManager()
        fixed = mgr.fix_arguments("deep_scrape", {"url": "http://x", "description": "get title"})
        assert "info_to_extract" in fixed
        assert "description" not in fixed
        assert fixed["url"] == "http://x"

    def test_fix_integrated_in_execute(self):
        """execute_tool 内部自动调用 fix_arguments"""
        mgr = BlogToolManager()
        received = {}

        def search_fn(query=""):
            received["query"] = query
            return query

        mgr.register("web_search", search_fn, description="搜索")
        result = mgr.execute_tool("web_search", q="test")
        assert result["success"] is True
        assert received["query"] == "test"
