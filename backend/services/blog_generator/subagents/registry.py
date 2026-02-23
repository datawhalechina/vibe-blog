"""
子代理注册表（1002.13）

全局注册表，支持按名称注册、查找和列出子代理配置。
借鉴 DeerFlow SubagentRegistry 的设计。
"""

import logging
from typing import Dict, List, Optional

from .config import SubagentConfig

logger = logging.getLogger(__name__)

_registry: Dict[str, SubagentConfig] = {}


def register_subagent(config: SubagentConfig) -> None:
    """注册子代理配置"""
    _registry[config.name] = config
    logger.info(f"[SubagentRegistry] 注册子代理: {config.name}")


def get_subagent_config(name: str) -> Optional[SubagentConfig]:
    """按名称查找子代理配置"""
    return _registry.get(name)


def list_subagents() -> List[SubagentConfig]:
    """列出所有已注册子代理"""
    return list(_registry.values())
