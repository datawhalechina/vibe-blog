"""MCP 客户端参数构建"""

import logging
from typing import Any, Dict

from .config import McpConfig, McpServerConfig

logger = logging.getLogger(__name__)


def build_server_params(server_name: str, config: McpServerConfig) -> Dict[str, Any]:
    """构建 MultiServerMCPClient 所需的服务器参数"""
    transport_type = config.type or "stdio"
    params: Dict[str, Any] = {"transport": transport_type}

    if transport_type == "stdio":
        if not config.command:
            raise ValueError(
                f"MCP server '{server_name}' with stdio transport requires 'command' field"
            )
        params["command"] = config.command
        params["args"] = config.args
        if config.env:
            params["env"] = config.env
    elif transport_type in ("sse", "http"):
        if not config.url:
            raise ValueError(
                f"MCP server '{server_name}' with {transport_type} transport requires 'url' field"
            )
        params["url"] = config.url
        if config.headers:
            params["headers"] = config.headers
    else:
        raise ValueError(
            f"MCP server '{server_name}' has unsupported transport type: {transport_type}"
        )

    return params


def build_servers_config(mcp_config: McpConfig) -> Dict[str, Dict[str, Any]]:
    """构建所有已启用 MCP 服务器的参数字典"""
    enabled = mcp_config.get_enabled_servers()
    if not enabled:
        logger.info("No enabled MCP servers found")
        return {}

    servers = {}
    for name, cfg in enabled.items():
        try:
            servers[name] = build_server_params(name, cfg)
            logger.info(f"Configured MCP server: {name}")
        except Exception as e:
            logger.error(f"Failed to configure MCP server '{name}': {e}")

    return servers
