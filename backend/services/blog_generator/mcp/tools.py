"""MCP 工具加载 — 通过 langchain-mcp-adapters 从 MCP 服务器获取 LangChain 工具"""

import logging
from typing import List

from .config import McpConfig
from .client import build_servers_config

logger = logging.getLogger(__name__)

# 检测 langchain-mcp-adapters 是否可用
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    _HAS_MCP_ADAPTERS = True
except ImportError:
    _HAS_MCP_ADAPTERS = False
    MultiServerMCPClient = None  # type: ignore


async def get_mcp_tools() -> List:
    """从所有已启用的 MCP 服务器加载 LangChain 工具

    每次调用从磁盘读取最新配置，确保外部修改立即生效。
    """
    if not _HAS_MCP_ADAPTERS:
        logger.warning(
            "langchain-mcp-adapters not installed. "
            "Install it to enable MCP tools: pip install langchain-mcp-adapters"
        )
        return []

    mcp_config = McpConfig.from_file()
    servers_config = build_servers_config(mcp_config)

    if not servers_config:
        logger.info("No enabled MCP servers configured")
        return []

    try:
        logger.info(f"Initializing MCP client with {len(servers_config)} server(s)")
        client = MultiServerMCPClient(servers_config)
        tools = await client.get_tools()
        logger.info(f"Loaded {len(tools)} tool(s) from MCP servers")
        return tools
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
        return []
