"""
Agent 模块 - 各专业 Agent 实现。

保持懒加载，避免只导入单个 agent 或 dispatcher 时触发整组可选依赖初始化。
"""

from importlib import import_module

_EXPORTS = {
    "ResearcherAgent": ("services.blog_generator.agents.researcher", "ResearcherAgent"),
    "PlannerAgent": ("services.blog_generator.agents.planner", "PlannerAgent"),
    "WriterAgent": ("services.blog_generator.agents.writer", "WriterAgent"),
    "CoderAgent": ("services.blog_generator.agents.coder", "CoderAgent"),
    "ArtistAgent": ("services.blog_generator.agents.artist", "ArtistAgent"),
    "QuestionerAgent": ("services.blog_generator.agents.questioner", "QuestionerAgent"),
    "ReviewerAgent": ("services.blog_generator.agents.reviewer", "ReviewerAgent"),
    "AssemblerAgent": ("services.blog_generator.agents.assembler", "AssemblerAgent"),
    "SearchCoordinator": (
        "services.blog_generator.agents.search_coordinator",
        "SearchCoordinator",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
