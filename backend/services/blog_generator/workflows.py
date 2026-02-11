"""
工作流注册 — 注册 6 种预定义工作流

每种工作流绑定默认 StyleProfile，用户可覆盖。
向后兼容：target_length 参数自动映射到对应工作流。
"""

from .workflow_registry import WorkflowRegistry
from .style_profile import StyleProfile


@WorkflowRegistry.register(
    "mini",
    default_style=StyleProfile.mini(),
    description="Mini 精品短文（800字，4章节，1轮修订）",
)
def create_mini_workflow(style: StyleProfile):
    return style


@WorkflowRegistry.register(
    "short",
    default_style=StyleProfile.short(),
    description="短文（1500字，2章节，1轮修订）",
)
def create_short_workflow(style: StyleProfile):
    return style


@WorkflowRegistry.register(
    "medium",
    default_style=StyleProfile.medium(),
    description="标准博客（3500字，4章节，3轮修订）",
)
def create_medium_workflow(style: StyleProfile):
    return style


@WorkflowRegistry.register(
    "long",
    default_style=StyleProfile.long(),
    description="长文（6000字，6章节，5轮修订）",
)
def create_long_workflow(style: StyleProfile):
    return style


@WorkflowRegistry.register(
    "deep",
    default_style=StyleProfile.deep_analysis(),
    description="深度分析（6000字，全部增强Agent + FactCheck）",
)
def create_deep_workflow(style: StyleProfile):
    return style


@WorkflowRegistry.register(
    "science",
    default_style=StyleProfile.science_popular(),
    description="科普内容（3500字，友好文风，多配图）",
)
def create_science_workflow(style: StyleProfile):
    return style
