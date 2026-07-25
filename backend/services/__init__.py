"""
vibe-blog 服务模块。

保持旧的 `from services import ...` API，同时避免在包导入时急切加载
可选依赖（例如 requests / Flask 扩展），这样测试可以只导入需要的子模块。
"""

from importlib import import_module

_EXPORTS = {
    "LLMService": ("services.llm", "LLMService"),
    "get_llm_service": ("services.llm", "get_llm_service"),
    "init_llm_service": ("services.llm", "init_llm_service"),
    "TransformService": ("services.transform_service", "TransformService"),
    "create_transform_service": ("services.transform_service", "create_transform_service"),
    "NanoBananaService": ("services.media", "NanoBananaService"),
    "get_image_service": ("services.media", "get_image_service"),
    "init_image_service": ("services.media", "init_image_service"),
    "AspectRatio": ("services.media", "AspectRatio"),
    "ImageSize": ("services.media", "ImageSize"),
    "STORYBOOK_STYLE_PREFIX": ("services.media", "STORYBOOK_STYLE_PREFIX"),
    "TaskManager": ("services.task_service", "TaskManager"),
    "get_task_manager": ("services.task_service", "get_task_manager"),
    "PipelineService": ("services.pipeline_service", "PipelineService"),
    "create_pipeline_service": ("services.pipeline_service", "create_pipeline_service"),
    "BlogGenerator": ("services.blog_generation", "BlogGenerator"),
    "SearchService": ("services.blog_generation", "SearchService"),
    "init_search_service": ("services.blog_generation", "init_search_service"),
    "get_search_service": ("services.blog_generation", "get_search_service"),
    "BlogService": ("services.blog_generation", "BlogService"),
    "init_blog_service": ("services.blog_generation", "init_blog_service"),
    "get_blog_service": ("services.blog_generation", "get_blog_service"),
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
