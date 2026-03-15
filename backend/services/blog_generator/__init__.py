"""
长文博客生成器 - Multi-Agent 协同生成系统。

这里保留旧导出接口，但避免包导入时立刻加载 `generator.py`，否则仅导入并行执行器、
prompt manager 等轻量模块时也会被 `langgraph` 等可选依赖阻塞。
"""

from importlib import import_module

_EXPORTS = {
    "BlogGenerator": ("services.blog_generator.generator", "BlogGenerator"),
    "SearchService": ("services.blog_generator.services.search_service", "SearchService"),
    "init_search_service": (
        "services.blog_generator.services.search_service",
        "init_search_service",
    ),
    "get_search_service": (
        "services.blog_generator.services.search_service",
        "get_search_service",
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
