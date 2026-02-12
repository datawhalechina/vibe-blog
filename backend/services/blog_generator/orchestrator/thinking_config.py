"""
37.03 推理引擎 Extended Thinking — Agent 场景化配置

按 Agent 角色决定是否启用 Claude Extended Thinking 模式：
- Planner / Reviewer / Questioner：需要深度推理，启用
- Writer / Artist：成本高收益低，禁用
"""

# Agent 级别 Thinking 开关
AGENT_THINKING_CONFIG = {
    "planner": True,
    "reviewer": True,
    "questioner": True,
    "writer": False,
    "artist": False,
}


def should_use_thinking(agent_name: str, global_enabled: bool = True) -> bool:
    """判断指定 Agent 是否应启用 Thinking 模式

    Args:
        agent_name: Agent 名称（如 planner / writer）
        global_enabled: 全局开关（THINKING_ENABLED 环境变量）

    Returns:
        True 表示应启用 Thinking
    """
    if not global_enabled:
        return False
    return AGENT_THINKING_CONFIG.get(agent_name, False)


def supports_thinking(model_name: str) -> bool:
    """检查模型是否支持 Extended Thinking

    目前仅 Claude 系列模型支持。

    Args:
        model_name: 模型名称（如 claude-3-5-sonnet-20241022）

    Returns:
        True 表示支持
    """
    if not model_name:
        return False
    name = model_name.lower()
    return "claude" in name
