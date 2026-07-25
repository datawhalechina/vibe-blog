"""Stable public boundary for blog quality review capabilities."""

from importlib import import_module


_EXPORTS = {
    "ReviewerAgent": (
        "services.blog_generator.agents.reviewer",
        "ReviewerAgent",
    ),
    "get_guidelines": (
        "services.blog_generator.review_guidelines",
        "get_guidelines",
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
