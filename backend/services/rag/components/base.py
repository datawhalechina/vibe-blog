"""
RAG 组件基类

对标 DeepTutor src/services/rag/components/base.py
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Component(Protocol):
    """组件协议"""
    name: str

    async def process(self, data: Any, **kwargs) -> Any:
        ...


class BaseComponent:
    """组件基类"""
    name: str = "base"

    async def process(self, data: Any, **kwargs) -> Any:
        raise NotImplementedError(f"{self.__class__.__name__}.process() not implemented")
