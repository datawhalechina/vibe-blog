"""
动态工具聚合器测试 — TDD 驱动

测试 get_available_tools() 统一聚合配置工具、内置工具、MCP 工具的能力。
"""

import os
import tempfile
import time
import pytest
from unittest.mock import MagicMock, patch

import yaml


# ===== Fixtures =====


@pytest.fixture(autouse=True)
def _reset_aggregator():
    """每个测试前重置聚合器全局状态"""
    from services.blog_generator.tools.aggregator import (
        _BUILTIN_TOOLS,
        _CONDITIONAL_TOOLS,
    )

    _BUILTIN_TOOLS.clear()
    _CONDITIONAL_TOOLS.clear()
    yield
    _BUILTIN_TOOLS.clear()
    _CONDITIONAL_TOOLS.clear()


@pytest.fixture
def mock_registry():
    """模拟 ToolRegistry，避免真实 YAML 加载"""
    mock_reg = MagicMock()
    mock_search = MagicMock()
    mock_search.name = "zhipu_search"
    mock_search.group = "search"
    mock_search.search = MagicMock()

    mock_crawl = MagicMock()
    mock_crawl.name = "jina_reader"
    mock_crawl.group = "crawl"
    mock_crawl.scrape = MagicMock()

    mock_reg.list_tools.return_value = ["zhipu_search", "jina_reader"]
    mock_reg.get_tool.side_effect = lambda n: {
        "zhipu_search": mock_search,
        "jina_reader": mock_crawl,
    }.get(n)
    mock_reg.get_tools_by_group.side_effect = lambda g: {
        "search": [mock_search],
        "crawl": [mock_crawl],
    }.get(g, [])

    return mock_reg


@pytest.fixture
def fake_builtin_tool():
    tool = MagicMock()
    tool.name = "source_citation"
    return tool


@pytest.fixture
def fake_conditional_tool():
    tool = MagicMock()
    tool.name = "deep_scrape"
    return tool


# ===== 核心聚合测试 =====


class TestGetAvailableTools:
    """get_available_tools() 核心聚合逻辑"""

    def test_returns_all_config_tools(self, mock_registry):
        """无过滤时返回所有配置工具"""
        from services.blog_generator.tools.aggregator import get_available_tools

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools()

        assert len(tools) == 2
        names = [t.name for t in tools]
        assert "zhipu_search" in names
        assert "jina_reader" in names

    def test_group_filter_search_only(self, mock_registry):
        """groups=["search"] 只返回搜索组"""
        from services.blog_generator.tools.aggregator import get_available_tools

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(groups=["search"])

        assert len(tools) == 1
        assert tools[0].name == "zhipu_search"

    def test_group_filter_multiple(self, mock_registry):
        """groups=["search", "crawl"] 返回两组"""
        from services.blog_generator.tools.aggregator import get_available_tools

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(groups=["search", "crawl"])

        assert len(tools) == 2

    def test_builtin_always_present(self, mock_registry, fake_builtin_tool):
        """内置工具始终出现在聚合结果中"""
        from services.blog_generator.tools.aggregator import (
            get_available_tools,
            register_builtin_tool,
        )

        register_builtin_tool(fake_builtin_tool)

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(groups=["search"])

        names = [t.name for t in tools]
        assert "source_citation" in names
        assert "zhipu_search" in names

    def test_builtin_present_even_without_groups(self, mock_registry, fake_builtin_tool):
        """无 groups 过滤时内置工具也在"""
        from services.blog_generator.tools.aggregator import (
            get_available_tools,
            register_builtin_tool,
        )

        register_builtin_tool(fake_builtin_tool)

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools()

        names = [t.name for t in tools]
        assert "source_citation" in names
        assert len(tools) == 3  # 2 config + 1 builtin


# ===== 条件注入测试 =====


class TestConditionalInjection:
    """条件工具注入"""

    def test_conditional_injected_when_true(self, mock_registry, fake_conditional_tool):
        """conditions={"deep_scrape": True} 注入条件工具"""
        from services.blog_generator.tools.aggregator import (
            get_available_tools,
            register_conditional_tool,
        )

        register_conditional_tool("deep_scrape", fake_conditional_tool)

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(conditions={"deep_scrape": True})

        names = [t.name for t in tools]
        assert "deep_scrape" in names

    def test_conditional_not_injected_when_false(self, mock_registry, fake_conditional_tool):
        """conditions={"deep_scrape": False} 不注入"""
        from services.blog_generator.tools.aggregator import (
            get_available_tools,
            register_conditional_tool,
        )

        register_conditional_tool("deep_scrape", fake_conditional_tool)

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(conditions={"deep_scrape": False})

        names = [t.name for t in tools]
        assert "deep_scrape" not in names

    def test_conditional_not_injected_when_missing(self, mock_registry, fake_conditional_tool):
        """未注册的条件 key 不报错"""
        from services.blog_generator.tools.aggregator import get_available_tools

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(conditions={"nonexistent": True})

        # 只有配置工具，无条件工具
        assert len(tools) == 2


# ===== MCP 占位测试 =====


class TestMcpPlaceholder:
    """MCP 工具集成占位"""

    def test_include_mcp_no_error(self, mock_registry):
        """include_mcp=True 不报错，返回空 MCP 列表"""
        from services.blog_generator.tools.aggregator import get_available_tools

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            tools = get_available_tools(include_mcp=True)

        # 只有配置工具（MCP 返回空列表）
        assert len(tools) == 2

    def test_mcp_tools_appended(self, mock_registry):
        """MCP 工具被追加到聚合结果"""
        from services.blog_generator.tools.aggregator import get_available_tools

        mock_mcp_tool = MagicMock()
        mock_mcp_tool.name = "mcp_calculator"

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ), patch(
            "services.blog_generator.tools.aggregator._get_mcp_tools",
            return_value=[mock_mcp_tool],
        ):
            tools = get_available_tools(include_mcp=True)

        names = [t.name for t in tools]
        assert "mcp_calculator" in names
        assert len(tools) == 3


# ===== 注册接口测试 =====


class TestRegistration:
    """register_builtin_tool / register_conditional_tool"""

    def test_register_builtin(self, fake_builtin_tool):
        from services.blog_generator.tools.aggregator import (
            _BUILTIN_TOOLS,
            register_builtin_tool,
        )

        register_builtin_tool(fake_builtin_tool)
        assert fake_builtin_tool in _BUILTIN_TOOLS

    def test_register_conditional(self, fake_conditional_tool):
        from services.blog_generator.tools.aggregator import (
            _CONDITIONAL_TOOLS,
            register_conditional_tool,
        )

        register_conditional_tool("deep_scrape", fake_conditional_tool)
        assert _CONDITIONAL_TOOLS["deep_scrape"] is fake_conditional_tool


# ===== 配置热重载测试 =====


class TestConfigStaleDetection:
    """ToolRegistry 配置文件变更检测"""

    def test_stale_detection_on_mtime_change(self):
        """修改 YAML 文件后 _is_config_stale() 返回 True"""
        from services.blog_generator.tools.registry import ToolRegistry

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"tool_groups": [], "tools": []}, f)
            tmp_path = f.name

        try:
            reg = ToolRegistry()
            reg.load_from_yaml(tmp_path)
            assert not reg._is_config_stale()

            # 模拟文件修改（确保 mtime 变化）
            time.sleep(0.05)
            with open(tmp_path, "w") as f:
                yaml.dump({"tool_groups": [], "tools": []}, f)

            assert reg._is_config_stale()
        finally:
            os.unlink(tmp_path)

    def test_auto_reload_on_stale(self):
        """聚合时配置过期自动重载"""
        from services.blog_generator.tools.aggregator import get_available_tools

        mock_reg = MagicMock()
        mock_reg.list_tools.return_value = []
        mock_reg._is_config_stale.return_value = True

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_reg,
        ):
            get_available_tools()

        mock_reg.reload.assert_called_once()

    def test_no_reload_when_fresh(self):
        """配置未过期不重载"""
        from services.blog_generator.tools.aggregator import get_available_tools

        mock_reg = MagicMock()
        mock_reg.list_tools.return_value = []
        mock_reg._is_config_stale.return_value = False

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_reg,
        ):
            get_available_tools()

        mock_reg.reload.assert_not_called()


# ===== BlogToolManager 桥接测试 =====


class TestSyncToToolManager:
    """sync_to_tool_manager() 桥接"""

    def test_search_tools_synced(self, mock_registry):
        """搜索工具桥接到 BlogToolManager"""
        from services.blog_generator.tools.aggregator import sync_to_tool_manager
        from utils.tool_manager import BlogToolManager

        manager = BlogToolManager()

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            sync_to_tool_manager(manager, groups=["search"])

        tool_names = [t["name"] for t in manager.get_all_tools()]
        assert "zhipu_search" in tool_names

    def test_crawl_tools_synced(self, mock_registry):
        """爬虫工具桥接到 BlogToolManager"""
        from services.blog_generator.tools.aggregator import sync_to_tool_manager
        from utils.tool_manager import BlogToolManager

        manager = BlogToolManager()

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            sync_to_tool_manager(manager, groups=["crawl"])

        tool_names = [t["name"] for t in manager.get_all_tools()]
        assert "jina_reader" in tool_names

    def test_all_tools_synced(self, mock_registry):
        """全部工具桥接"""
        from services.blog_generator.tools.aggregator import sync_to_tool_manager
        from utils.tool_manager import BlogToolManager

        manager = BlogToolManager()

        with patch(
            "services.blog_generator.tools.aggregator.get_tool_registry",
            return_value=mock_registry,
        ):
            sync_to_tool_manager(manager)

        tool_names = [t["name"] for t in manager.get_all_tools()]
        assert "zhipu_search" in tool_names
        assert "jina_reader" in tool_names
