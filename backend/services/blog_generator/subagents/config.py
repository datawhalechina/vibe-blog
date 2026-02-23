"""
子代理配置定义（1002.13）

借鉴 DeerFlow SubagentConfig 的设计，定义子代理的
system_prompt、工具白/黑名单、模型继承、超时等配置。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SubagentConfig:
    """子代理配置。

    Attributes:
        name: 子代理唯一标识（如 "researcher", "writer", "factcheck"）
        description: 何时应委托给此子代理
        system_prompt: 子代理的系统提示词
        tools: 允许使用的工具名列表，None 表示继承全部
        disallowed_tools: 禁止使用的工具名列表
        model: 模型名称，"inherit" 表示继承父代理模型
        max_turns: 最大 LLM 调用轮次（防无限循环）
        timeout_seconds: 执行超时（秒）
    """
    name: str
    description: str
    system_prompt: str
    tools: Optional[List[str]] = None
    disallowed_tools: Optional[List[str]] = field(
        default_factory=lambda: ["delegate_task"]
    )
    model: str = "inherit"
    max_turns: int = 30
    timeout_seconds: int = 300
