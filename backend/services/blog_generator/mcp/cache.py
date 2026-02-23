"""MCP 工具缓存 — 线程安全懒加载 + mtime 失效检测，适配 Flask 同步架构"""

import asyncio
import logging
import os
import threading
from typing import List, Optional

logger = logging.getLogger(__name__)


class McpToolsCache:
    """线程安全的 MCP 工具缓存"""

    def __init__(self):
        self._tools: Optional[List] = None
        self._initialized = False
        self._config_mtime: Optional[float] = None
        self._lock = threading.Lock()

    def get_tools(self) -> List:
        """获取缓存的 MCP 工具（主入口）"""
        with self._lock:
            if self._is_stale():
                logger.info("MCP config changed, resetting cache")
                self._reset()
            if not self._initialized:
                self._lazy_init()
            return self._tools or []

    def _is_stale(self) -> bool:
        if not self._initialized:
            return False
        from .config import McpConfig
        path = McpConfig._resolve_path()
        if path is None or self._config_mtime is None:
            return False
        current = os.path.getmtime(path)
        return current > self._config_mtime

    def _lazy_init(self):
        """在新事件循环中运行异步加载"""
        try:
            from .tools import get_mcp_tools
            loop = asyncio.new_event_loop()
            try:
                self._tools = loop.run_until_complete(get_mcp_tools())
            finally:
                loop.close()
            self._initialized = True
            from .config import McpConfig
            path = McpConfig._resolve_path()
            self._config_mtime = os.path.getmtime(path) if path else None
            logger.info(f"MCP tools loaded: {len(self._tools or [])} tool(s)")
        except Exception as e:
            logger.error(f"MCP tools load failed: {e}")
            self._tools = []
            self._initialized = True

    def _reset(self):
        self._tools = None
        self._initialized = False
        self._config_mtime = None

    def reset(self):
        """公开重置接口"""
        with self._lock:
            self._reset()


# 全局单例
_cache = McpToolsCache()


def get_cached_mcp_tools() -> List:
    return _cache.get_tools()


def reset_mcp_cache():
    _cache.reset()
