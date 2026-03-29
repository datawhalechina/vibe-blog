"""
41.06 三级 LLM 模型策略 — Agent 级别注册表

每个 Agent 的默认模型级别在此集中管理。
支持环境变量覆盖：AGENT_{NAME}_LLM_TIER=fast|smart|strategic
"""

import os

# Agent 名称 → 默认模型级别
AGENT_LLM_TIERS = {
    # strategic: 需要多步推理的规划任务
    'planner': 'strategic',
    'search_coordinator': 'strategic',

    # smart: 需要高质量输出的核心任务
    'writer': 'smart',
    'reviewer': 'smart',
    'humanizer': 'smart',
    'questioner': 'smart',
    'coder': 'smart',
    'factcheck': 'smart',
    'thread_checker': 'smart',
    'voice_checker': 'smart',

    # fast: 简单的格式化/摘要任务
    'researcher': 'fast',
    'artist': 'fast',
    'summary_generator': 'fast',
}


def get_agent_tier(agent_name: str) -> str:
    """获取 Agent 的模型级别（支持环境变量覆盖）

    环境变量格式：AGENT_PLANNER_LLM_TIER=smart
    """
    env_key = f"AGENT_{agent_name.upper()}_LLM_TIER"
    env_val = os.getenv(env_key, '').lower()
    if env_val in ('fast', 'smart', 'strategic'):
        return env_val
    return AGENT_LLM_TIERS.get(agent_name, 'smart')
