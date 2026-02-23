"""
1003.15 研究预设系统

迁移自 DeepTutor research presets，适配 vibe-blog 博客生成管线。
提供 quick/medium/deep/auto 四种研究深度预设。
"""

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


@dataclass
class ResearchPreset:
    """研究深度预设配置"""
    name: str
    description: str
    max_search_count: int
    deep_research_max_rounds: int
    depth_requirement: Literal["minimal", "shallow", "medium", "deep"]
    iteration_mode: Literal["fixed", "flexible"] = "fixed"


RESEARCH_PRESETS: Dict[str, ResearchPreset] = {
    "quick": ResearchPreset(
        name="quick",
        description="快速研究 - 最少搜索，快速出稿",
        max_search_count=1,
        deep_research_max_rounds=1,
        depth_requirement="minimal",
        iteration_mode="fixed",
    ),
    "medium": ResearchPreset(
        name="medium",
        description="标准研究 - 平衡深度与速度",
        max_search_count=4,
        deep_research_max_rounds=2,
        depth_requirement="medium",
        iteration_mode="fixed",
    ),
    "deep": ResearchPreset(
        name="deep",
        description="深度研究 - 最大搜索深度，全面覆盖",
        max_search_count=8,
        deep_research_max_rounds=4,
        depth_requirement="deep",
        iteration_mode="fixed",
    ),
    "auto": ResearchPreset(
        name="auto",
        description="自适应研究 - Agent 自动判断何时停止",
        max_search_count=6,
        deep_research_max_rounds=3,
        depth_requirement="medium",
        iteration_mode="flexible",
    ),
}


def get_research_preset(name: str) -> Optional[ResearchPreset]:
    return RESEARCH_PRESETS.get(name)


def get_preset_names() -> List[str]:
    return list(RESEARCH_PRESETS.keys())


def apply_preset_to_state(state: dict, preset_name: str) -> dict:
    """Apply a research preset to a state dict, overriding relevant fields."""
    preset = get_research_preset(preset_name)
    if preset is None:
        return state
    state["max_search_count"] = preset.max_search_count
    state["research_preset_name"] = preset.name
    state["iteration_mode"] = preset.iteration_mode
    return state
