"""
动态工具聚合器 — 统一聚合配置工具、内置工具、MCP 工具

提供 get_available_tools() 统一入口，支持：
- 配置驱动工具（从 ToolRegistry / tool_config.yaml）
- 内置工具（始终可用）
- 条件工具（按运行时参数注入）
- MCP 工具（通过 mcp 模块加载）
- 分组过滤
- 配置热重载检测
"""

import logging
from typing import Any, Dict, List, Optional

from .registry import get_tool_registry

logger = logging.getLogger(__name__)

# 内置工具注册表 — 始终可用的工具
_BUILTIN_TOOLS: List[Any] = []
# 条件工具注册表 — 按条件注入
_CONDITIONAL_TOOLS: Dict[str, Any] = {}


def register_builtin_tool(tool: Any) -> None:
    """注册内置工具（应用启动时调用）"""
    _BUILTIN_TOOLS.append(tool)
    logger.info(f"注册内置工具: {getattr(tool, 'name', str(tool))}")


def register_conditional_tool(condition_key: str, tool: Any) -> None:
    """注册条件工具（如 vision_tool, subagent_tool）"""
    _CONDITIONAL_TOOLS[condition_key] = tool
    logger.info(f"注册条件工具: {condition_key}")


def get_available_tools(
    groups: Optional[List[str]] = None,
    include_mcp: bool = False,
    conditions: Optional[Dict[str, bool]] = None,
) -> List[Any]:
    """
    动态聚合所有可用工具。

    Args:
        groups: 工具组过滤（None = 全部配置工具）
        include_mcp: 是否包含 MCP 工具
        conditions: 条件注入开关，如 {"deep_scrape": True}

    Returns:
        聚合后的工具列表
    """
    conditions = conditions or {}
    tools: List[Any] = []

    # 0. 配置热重载检测
    registry = get_tool_registry()
    if registry._is_config_stale():
        logger.info("工具配置已变更，自动重载")
        registry.reload()

    # 1. 配置驱动工具（从 ToolRegistry）
    if groups:
        for group in groups:
            tools.extend(registry.get_tools_by_group(group))
    else:
        for name in registry.list_tools():
            tool = registry.get_tool(name)
            if tool is not None:
                tools.append(tool)

    # 2. 内置工具（始终注入）
    tools.extend(_BUILTIN_TOOLS)

    # 3. 条件工具
    for key, enabled in conditions.items():
        if enabled and key in _CONDITIONAL_TOOLS:
            tools.append(_CONDITIONAL_TOOLS[key])
            logger.debug(f"条件注入工具: {key}")

    # 4. MCP 工具
    if include_mcp:
        mcp_tools = _get_mcp_tools()
        tools.extend(mcp_tools)

    logger.info(
        f"工具聚合完成: {len(tools)} 个工具 "
        f"(配置={len(registry.list_tools())}, "
        f"内置={len(_BUILTIN_TOOLS)}, "
        f"条件={sum(1 for k, v in conditions.items() if v and k in _CONDITIONAL_TOOLS)})"
    )
    return tools


def _get_mcp_tools() -> List[Any]:
    """获取 MCP 工具（通过已实现的 mcp 模块）"""
    try:
        from ..mcp import get_cached_mcp_tools

        return get_cached_mcp_tools()
    except Exception as e:
        logger.warning(f"MCP 工具加载失败: {e}")
        return []


def sync_to_tool_manager(
    manager: Any,
    groups: Optional[List[str]] = None,
    conditions: Optional[Dict[str, bool]] = None,
) -> None:
    """
    将聚合工具同步到 BlogToolManager 执行层。

    自动检测工具类型（search/scrape），注册对应方法到 manager。
    """
    tools = get_available_tools(groups=groups, conditions=conditions)
    for tool in tools:
        if hasattr(tool, "search"):
            manager.register(
                tool.name, tool.search, description=f"搜索工具: {tool.name}"
            )
        elif hasattr(tool, "scrape"):
            manager.register(
                tool.name, tool.scrape, description=f"爬虫工具: {tool.name}"
            )
