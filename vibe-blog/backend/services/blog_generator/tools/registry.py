"""
ToolRegistry — 配置驱动的工具注册表

移植自 DeerFlow 的 resolve_variable + ToolConfig 模式。

职责：
1. 从 YAML 加载工具声明
2. 通过反射加载工具实例
3. 按组过滤工具
4. 支持运行时重载
"""

import logging
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .base import BaseCrawlTool, BaseSearchTool

logger = logging.getLogger(__name__)


class ToolConfig:
    """工具配置项"""

    def __init__(self, name: str, group: str, use: str, **extra):
        self.name = name
        self.group = group
        self.use = use
        self.extra = extra  # max_results, api_key, timeout 等


class ToolRegistry:
    """
    配置驱动的工具注册表

    从 YAML 加载工具声明，通过反射实例化，按组过滤。
    """

    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._configs: Dict[str, ToolConfig] = {}
        self._groups: Dict[str, List[str]] = {}
        self._config_path: Optional[str] = None

    def load_from_yaml(self, config_path: str = None) -> None:
        """从 YAML 文件加载工具配置"""
        if config_path is None:
            config_path = self._config_path or os.environ.get(
                "VIBE_BLOG_TOOL_CONFIG",
                os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "tool_config.yaml"
                ),
            )
        self._config_path = config_path

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"工具配置文件不存在: {config_path}")
            return

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # 解析环境变量
        data = self._resolve_env_vars(data)

        # 加载工具组
        for group in data.get("tool_groups", []):
            self._groups.setdefault(group["name"], [])

        # 加载工具
        for tool_data in data.get("tools", []):
            tool_data = dict(tool_data)  # 避免修改原始数据
            name = tool_data.pop("name")
            group = tool_data.pop("group")
            use = tool_data.pop("use")
            config = ToolConfig(name=name, group=group, use=use, **tool_data)
            self._configs[name] = config
            self._groups.setdefault(group, []).append(name)

            # 反射加载
            try:
                tool = self._resolve_variable(use, config)
                self._tools[name] = tool
                logger.info(f"工具加载成功: {name} ({use})")
            except Exception as e:
                logger.error(f"工具加载失败: {name} ({use}): {e}")

    def _resolve_variable(self, variable_path: str, config: ToolConfig) -> Any:
        """反射加载工具（移植自 DeerFlow resolve_variable）"""
        module_path, variable_name = variable_path.rsplit(":", 1)
        module = import_module(module_path)
        tool_class_or_instance = getattr(module, variable_name)

        # 如果是类，用 config.extra 实例化
        if isinstance(tool_class_or_instance, type):
            return tool_class_or_instance(**config.extra)
        # 如果是实例，注入配置
        if hasattr(tool_class_or_instance, "configure"):
            tool_class_or_instance.configure(config.extra)
        return tool_class_or_instance

    def _resolve_env_vars(self, data: Any) -> Any:
        """递归解析 $ENV_VAR 引用"""
        if isinstance(data, str) and data.startswith("$"):
            return os.getenv(data[1:], "")
        elif isinstance(data, dict):
            return {k: self._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_vars(item) for item in data]
        return data

    # ===== 查询接口 =====

    def get_tool(self, name: str) -> Optional[Any]:
        """按名称获取工具"""
        return self._tools.get(name)

    def get_tools_by_group(self, group: str) -> List[Any]:
        """按组获取工具列表"""
        names = self._groups.get(group, [])
        return [self._tools[n] for n in names if n in self._tools]

    def get_search_tools(self) -> List[BaseSearchTool]:
        """获取所有搜索工具"""
        return self.get_tools_by_group("search")

    def get_crawl_tools(self) -> List[BaseCrawlTool]:
        """获取所有爬虫工具"""
        return self.get_tools_by_group("crawl")

    def get_available_search_tools(self) -> List[BaseSearchTool]:
        """获取所有可用的搜索工具（API Key 已配置）"""
        return [t for t in self.get_search_tools() if t.is_available()]

    def get_tool_config(self, name: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._configs.get(name)

    def list_tools(self) -> List[str]:
        """列出所有已加载工具名"""
        return list(self._tools.keys())

    def reload(self) -> None:
        """重新加载配置"""
        self._tools.clear()
        self._configs.clear()
        self._groups.clear()
        self.load_from_yaml()


# ===== 全局单例 =====

_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表单例"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry.load_from_yaml()
    return _registry


def reset_tool_registry() -> None:
    """重置注册表（测试用）"""
    global _registry
    _registry = None
