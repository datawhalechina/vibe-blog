"""
MCP 协议集成 — 单元测试

测试覆盖:
- McpServerConfig / McpConfig 配置模型
- build_server_params / build_servers_config 客户端构建
- McpToolsCache 缓存与懒加载
- get_mcp_tools 工具加载（mock）
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# 1. 配置模型测试
# ============================================================

class TestMcpServerConfig:
    """McpServerConfig Pydantic 模型"""

    def test_default_values(self):
        from services.blog_generator.mcp.config import McpServerConfig
        cfg = McpServerConfig()
        assert cfg.enabled is True
        assert cfg.type == "stdio"
        assert cfg.command is None
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.url is None
        assert cfg.headers == {}
        assert cfg.description == ""

    def test_stdio_config(self):
        from services.blog_generator.mcp.config import McpServerConfig
        cfg = McpServerConfig(
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        )
        assert cfg.command == "npx"
        assert len(cfg.args) == 3

    def test_sse_config(self):
        from services.blog_generator.mcp.config import McpServerConfig
        cfg = McpServerConfig(
            type="sse",
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token123"},
        )
        assert cfg.url == "https://api.example.com/mcp"
        assert "Authorization" in cfg.headers

    def test_http_config(self):
        from services.blog_generator.mcp.config import McpServerConfig
        cfg = McpServerConfig(
            type="http",
            url="http://localhost:8080/mcp",
        )
        assert cfg.type == "http"
        assert cfg.url == "http://localhost:8080/mcp"

    def test_disabled_server(self):
        from services.blog_generator.mcp.config import McpServerConfig
        cfg = McpServerConfig(enabled=False, type="sse", url="http://x")
        assert cfg.enabled is False


class TestMcpConfig:
    """McpConfig 聚合配置"""

    def test_from_empty_file(self, tmp_path):
        from services.blog_generator.mcp.config import McpConfig
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text('{"mcpServers": {}}')
        cfg = McpConfig.from_file(str(config_file))
        assert cfg.mcp_servers == {}

    def test_from_file_with_servers(self, tmp_path):
        from services.blog_generator.mcp.config import McpConfig
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps({
            "mcpServers": {
                "fs": {"type": "stdio", "command": "npx", "args": ["-y", "fs-server"]},
                "disabled": {"enabled": False, "type": "sse", "url": "http://x"},
            }
        }))
        cfg = McpConfig.from_file(str(config_file))
        assert len(cfg.mcp_servers) == 2
        enabled = cfg.get_enabled_servers()
        assert len(enabled) == 1
        assert "fs" in enabled

    def test_env_var_resolution(self, tmp_path, monkeypatch):
        from services.blog_generator.mcp.config import McpConfig
        monkeypatch.setenv("MY_TOKEN", "secret123")
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps({
            "mcpServers": {
                "gh": {
                    "type": "stdio", "command": "npx",
                    "args": ["-y", "gh-server"],
                    "env": {"GITHUB_TOKEN": "$MY_TOKEN"},
                }
            }
        }))
        cfg = McpConfig.from_file(str(config_file))
        assert cfg.mcp_servers["gh"].env["GITHUB_TOKEN"] == "secret123"

    def test_missing_file_returns_empty(self):
        from services.blog_generator.mcp.config import McpConfig
        cfg = McpConfig.from_file("/nonexistent/path.json")
        assert cfg.mcp_servers == {}

    def test_resolve_path_explicit(self, tmp_path):
        from services.blog_generator.mcp.config import McpConfig
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text('{"mcpServers": {}}')
        path = McpConfig._resolve_path(str(config_file))
        assert path is not None

    def test_resolve_path_env_var(self, tmp_path, monkeypatch):
        from services.blog_generator.mcp.config import McpConfig
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text('{"mcpServers": {}}')
        monkeypatch.setenv("VIBE_BLOG_MCP_CONFIG", str(config_file))
        path = McpConfig._resolve_path()
        assert path is not None

    def test_resolve_path_none_when_missing(self, monkeypatch):
        from services.blog_generator.mcp.config import McpConfig
        monkeypatch.delenv("VIBE_BLOG_MCP_CONFIG", raising=False)
        # 确保 CWD 下没有 mcp_config.json
        path = McpConfig._resolve_path("/definitely/not/a/real/path.json")
        assert path is None


# ============================================================
# 2. 客户端构建测试
# ============================================================

class TestBuildServerParams:
    """build_server_params 参数构建"""

    def test_stdio_params(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(type="stdio", command="npx", args=["-y", "server"])
        params = build_server_params("test", cfg)
        assert params["transport"] == "stdio"
        assert params["command"] == "npx"
        assert params["args"] == ["-y", "server"]

    def test_stdio_with_env(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(
            type="stdio", command="npx", args=[],
            env={"TOKEN": "abc"},
        )
        params = build_server_params("test", cfg)
        assert params["env"] == {"TOKEN": "abc"}

    def test_sse_params(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(type="sse", url="https://api.example.com/mcp")
        params = build_server_params("test", cfg)
        assert params["transport"] == "sse"
        assert params["url"] == "https://api.example.com/mcp"

    def test_http_params_with_headers(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(
            type="http", url="http://localhost:8080/mcp",
            headers={"Authorization": "Bearer tok"},
        )
        params = build_server_params("test", cfg)
        assert params["transport"] == "http"
        assert params["headers"]["Authorization"] == "Bearer tok"

    def test_stdio_missing_command_raises(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(type="stdio")  # no command
        with pytest.raises(ValueError, match="requires 'command'"):
            build_server_params("bad", cfg)

    def test_sse_missing_url_raises(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(type="sse")  # no url
        with pytest.raises(ValueError, match="requires 'url'"):
            build_server_params("bad", cfg)

    def test_unsupported_transport_raises(self):
        from services.blog_generator.mcp.config import McpServerConfig
        from services.blog_generator.mcp.client import build_server_params
        cfg = McpServerConfig(type="grpc")
        with pytest.raises(ValueError, match="unsupported transport"):
            build_server_params("bad", cfg)


class TestBuildServersConfig:
    """build_servers_config 多服务器构建"""

    def test_builds_enabled_servers(self):
        from services.blog_generator.mcp.config import McpConfig, McpServerConfig
        from services.blog_generator.mcp.client import build_servers_config
        cfg = McpConfig(mcp_servers={
            "a": McpServerConfig(type="stdio", command="cmd", args=[]),
            "b": McpServerConfig(enabled=False, type="sse", url="http://x"),
        })
        result = build_servers_config(cfg)
        assert "a" in result
        assert "b" not in result

    def test_error_isolation(self):
        """单个服务器配置错误不影响其他"""
        from services.blog_generator.mcp.config import McpConfig, McpServerConfig
        from services.blog_generator.mcp.client import build_servers_config
        cfg = McpConfig(mcp_servers={
            "good": McpServerConfig(type="stdio", command="cmd", args=[]),
            "bad": McpServerConfig(type="stdio"),  # missing command
        })
        result = build_servers_config(cfg)
        assert "good" in result
        assert "bad" not in result

    def test_empty_config(self):
        from services.blog_generator.mcp.config import McpConfig
        from services.blog_generator.mcp.client import build_servers_config
        cfg = McpConfig(mcp_servers={})
        result = build_servers_config(cfg)
        assert result == {}


# ============================================================
# 3. 缓存与懒加载测试
# ============================================================

class TestMcpToolsCache:
    """McpToolsCache 缓存层"""

    def test_lazy_init_loads_tools(self):
        """首次 get_tools() 触发懒加载"""
        from services.blog_generator.mcp.cache import McpToolsCache
        cache = McpToolsCache()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"

        with patch("services.blog_generator.mcp.tools.get_mcp_tools",
                    new_callable=AsyncMock, return_value=[mock_tool]):
            tools = cache.get_tools()
            assert len(tools) == 1
            assert tools[0].name == "test_tool"

    def test_cache_returns_same_tools(self):
        """第二次调用返回缓存，不重新加载"""
        from services.blog_generator.mcp.cache import McpToolsCache
        cache = McpToolsCache()
        mock_tool = MagicMock()

        with patch("services.blog_generator.mcp.tools.get_mcp_tools",
                    new_callable=AsyncMock, return_value=[mock_tool]) as mock_get:
            cache.get_tools()
            cache.get_tools()
            assert mock_get.await_count == 1

    def test_reset_clears_cache(self):
        """reset() 清除缓存，下次调用重新加载"""
        from services.blog_generator.mcp.cache import McpToolsCache
        cache = McpToolsCache()
        mock_tool = MagicMock()

        with patch("services.blog_generator.mcp.tools.get_mcp_tools",
                    new_callable=AsyncMock, return_value=[mock_tool]) as mock_get:
            cache.get_tools()
            cache.reset()
            cache.get_tools()
            assert mock_get.await_count == 2

    def test_stale_cache_reloads(self, tmp_path):
        """配置文件变更后缓存自动失效"""
        from services.blog_generator.mcp.cache import McpToolsCache
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text('{"mcpServers": {}}')

        cache = McpToolsCache()
        cache._initialized = True
        cache._tools = []
        cache._config_mtime = config_file.stat().st_mtime - 10  # 旧 mtime

        with patch("services.blog_generator.mcp.config.McpConfig._resolve_path",
                    return_value=config_file):
            with patch("services.blog_generator.mcp.tools.get_mcp_tools",
                        new_callable=AsyncMock, return_value=[MagicMock()]):
                tools = cache.get_tools()
                assert len(tools) == 1  # 重新加载了

    def test_load_failure_returns_empty(self):
        """加载失败返回空列表"""
        from services.blog_generator.mcp.cache import McpToolsCache
        cache = McpToolsCache()

        with patch("services.blog_generator.mcp.tools.get_mcp_tools",
                    new_callable=AsyncMock, side_effect=Exception("boom")):
            tools = cache.get_tools()
            assert tools == []
            assert cache._initialized is True  # 标记已初始化，避免反复重试


# ============================================================
# 4. 工具加载测试（mock MultiServerMCPClient）
# ============================================================

class TestGetMcpTools:
    """get_mcp_tools 异步加载"""

    @pytest.mark.asyncio
    async def test_loads_tools_from_config(self, tmp_path):
        from services.blog_generator.mcp.tools import get_mcp_tools
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps({
            "mcpServers": {
                "test": {"type": "stdio", "command": "echo", "args": ["hello"]}
            }
        }))

        mock_tool = MagicMock()
        mock_client_instance = AsyncMock()
        mock_client_instance.get_tools = AsyncMock(return_value=[mock_tool])

        with patch("services.blog_generator.mcp.tools._HAS_MCP_ADAPTERS", True):
            with patch("services.blog_generator.mcp.config.McpConfig._resolve_path",
                        return_value=config_file):
                with patch("services.blog_generator.mcp.tools.MultiServerMCPClient",
                            return_value=mock_client_instance) as mock_cls:
                    tools = await get_mcp_tools()
                    assert len(tools) == 1
                    mock_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_servers_returns_empty(self, tmp_path):
        from services.blog_generator.mcp.tools import get_mcp_tools
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text('{"mcpServers": {}}')

        with patch("services.blog_generator.mcp.config.McpConfig._resolve_path",
                    return_value=config_file):
            tools = await get_mcp_tools()
            assert tools == []

    @pytest.mark.asyncio
    async def test_import_error_returns_empty(self):
        """langchain-mcp-adapters 未安装时优雅降级"""
        from services.blog_generator.mcp.tools import get_mcp_tools

        with patch("services.blog_generator.mcp.tools.MultiServerMCPClient",
                    side_effect=ImportError("no module")):
            # 需要让 import 失败 — 通过 patch _HAS_MCP_ADAPTERS
            with patch("services.blog_generator.mcp.tools._HAS_MCP_ADAPTERS", False):
                tools = await get_mcp_tools()
                assert tools == []


# ============================================================
# 5. 模块级公开 API 测试
# ============================================================

class TestMcpModuleApi:
    """mcp/__init__.py 公开 API"""

    def test_exports(self):
        from services.blog_generator.mcp import (
            get_cached_mcp_tools,
            reset_mcp_cache,
            get_mcp_tools,
            build_server_params,
            build_servers_config,
        )
        assert callable(get_cached_mcp_tools)
        assert callable(reset_mcp_cache)
        assert callable(get_mcp_tools)
        assert callable(build_server_params)
        assert callable(build_servers_config)


# ============================================================
# 6. 全局函数测试
# ============================================================

class TestGlobalFunctions:
    """模块级 get_cached_mcp_tools / reset_mcp_cache"""

    def test_get_cached_mcp_tools_returns_list(self):
        from services.blog_generator.mcp.cache import get_cached_mcp_tools, reset_mcp_cache
        reset_mcp_cache()
        with patch("services.blog_generator.mcp.tools.get_mcp_tools",
                    new_callable=AsyncMock, return_value=[]):
            tools = get_cached_mcp_tools()
            assert isinstance(tools, list)

    def test_reset_mcp_cache(self):
        from services.blog_generator.mcp.cache import reset_mcp_cache, _cache
        reset_mcp_cache()
        assert _cache._initialized is False
        assert _cache._tools is None
