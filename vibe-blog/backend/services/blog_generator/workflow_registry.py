"""
WorkflowRegistry — 装饰器模式注册不同类型的工作流

每个工作流有默认 StyleProfile，用户可以覆盖。
"""

from typing import Callable, Dict, Any, Optional
from .style_profile import StyleProfile


class WorkflowRegistry:
    """工作流注册器"""

    _workflows: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        default_style: Optional[StyleProfile] = None,
        description: str = "",
    ):
        """装饰器：注册工作流"""
        def decorator(func: Callable):
            cls._workflows[name] = {
                "factory": func,
                "default_style": default_style or StyleProfile(),
                "description": description,
            }
            return func
        return decorator

    @classmethod
    def get(cls, name: str, style: Optional[StyleProfile] = None) -> Any:
        """获取工作流实例（用户风格 > 工作流默认风格）"""
        if name not in cls._workflows:
            available = list(cls._workflows.keys())
            raise KeyError(f"工作流 '{name}' 不存在。可用: {available}")

        workflow = cls._workflows[name]
        final_style = style or workflow["default_style"]
        return workflow["factory"](final_style)

    @classmethod
    def list_workflows(cls) -> Dict[str, str]:
        """列出所有已注册的工作流"""
        return {
            name: info["description"]
            for name, info in cls._workflows.items()
        }

    @classmethod
    def get_default_style(cls, name: str) -> StyleProfile:
        """获取工作流的默认风格"""
        if name not in cls._workflows:
            raise KeyError(f"工作流 '{name}' 不存在")
        return cls._workflows[name]["default_style"]

    @classmethod
    def clear(cls):
        """清空注册（测试用）"""
        cls._workflows.clear()
