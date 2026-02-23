"""
子代理委托系统（1002.13）

提供子代理配置、注册表、执行器和并发限制，
支持博客生成管线中的动态任务委托。
"""

from .config import SubagentConfig
from .registry import register_subagent, get_subagent_config, list_subagents
from .executor import SubagentExecutor, get_background_task
from .limit_guard import SubagentLimitGuard
from .delegate import delegate_task

__all__ = [
    "SubagentConfig",
    "register_subagent",
    "get_subagent_config",
    "list_subagents",
    "SubagentExecutor",
    "get_background_task",
    "SubagentLimitGuard",
    "delegate_task",
]
