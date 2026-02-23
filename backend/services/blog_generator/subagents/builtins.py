"""
内置子代理定义（1002.13）

定义 vibe-blog 场景下的内置子代理类型，
在模块加载时自动注册到全局注册表。
"""

from .config import SubagentConfig
from .registry import register_subagent

BUILTIN_SUBAGENTS = [
    SubagentConfig(
        name="researcher",
        description="调研子代理 — 搜索和整理背景资料",
        system_prompt=(
            "你是一个专业的调研专家。你的任务是根据给定主题，"
            "搜索、整理和总结相关背景资料。输出结构化的调研报告，"
            "包含关键发现、数据来源和核心概念。"
        ),
        tools=["web_search", "crawl"],
        timeout_seconds=120,
        max_turns=10,
    ),
    SubagentConfig(
        name="writer",
        description="写作子代理 — 撰写博客章节内容",
        system_prompt=(
            "你是一个专业的技术写作专家。你的任务是根据大纲和背景资料，"
            "撰写高质量的博客章节内容。注意逻辑连贯、语言流畅、"
            "技术准确，并适当使用代码示例和图表说明。"
        ),
        timeout_seconds=180,
        max_turns=15,
    ),
    SubagentConfig(
        name="factcheck",
        description="事实核查子代理 — 验证内容中的事实性声明",
        system_prompt=(
            "你是一个严谨的事实核查专家。你的任务是检查给定内容中的"
            "事实性声明，标记可疑或不准确的信息，并提供修正建议。"
        ),
        tools=["web_search"],
        timeout_seconds=90,
        max_turns=10,
    ),
]


def register_builtins() -> None:
    """注册所有内置子代理"""
    for config in BUILTIN_SUBAGENTS:
        register_subagent(config)
