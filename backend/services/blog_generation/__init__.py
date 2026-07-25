"""Stable public boundary for the long-form blog generation capability."""

from importlib import import_module


_EXPORTS = {
    "BlogGenerator": ("services.blog_generator.generator", "BlogGenerator"),
    "BlogService": ("services.blog_generator.blog_service", "BlogService"),
    "SearchService": (
        "services.blog_generator.services.search_service",
        "SearchService",
    ),
    "extract_article_summary": (
        "services.blog_generator.blog_service",
        "extract_article_summary",
    ),
    "get_blog_service": (
        "services.blog_generator.blog_service",
        "get_blog_service",
    ),
    "get_prompt_manager": (
        "services.blog_generator.prompts",
        "get_prompt_manager",
    ),
    "get_search_service": (
        "services.blog_generator.services.search_service",
        "get_search_service",
    ),
    "init_blog_service": (
        "services.blog_generator.blog_service",
        "init_blog_service",
    ),
    "init_search_service": (
        "services.blog_generator.services.search_service",
        "init_search_service",
    ),
    "init_serper_service": (
        "services.blog_generator.services.serper_search_service",
        "init_serper_service",
    ),
    "init_sogou_service": (
        "services.blog_generator.services.sogou_search_service",
        "init_sogou_service",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
