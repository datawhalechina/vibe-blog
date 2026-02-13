"""
37.12 声明式编排引擎

- validate_config(): JSON Schema 校验
- resolve_extends(): 继承解析
- resolve_style_refs(): $style.* 引用解析
"""
import logging
from typing import Dict, Any, List

from .workflow_schema import validate_workflow_config

logger = logging.getLogger(__name__)


def resolve_style_refs(config: Any, style: Dict[str, Any]) -> Any:
    """递归解析 JSON 中的 $style.* 引用"""
    if isinstance(config, str) and config.startswith("$style."):
        field = config[7:]
        return style.get(field, config)
    elif isinstance(config, dict):
        return {k: resolve_style_refs(v, style) for k, v in config.items()}
    elif isinstance(config, list):
        return [resolve_style_refs(item, style) for item in config]
    return config


class DeclarativeEngine:
    """声明式编排引擎"""

    def __init__(self, config: dict):
        self.config = config

    def validate_config(self) -> List[str]:
        return validate_workflow_config(self.config)

    def resolve_extends(self, registry: Dict[str, dict]) -> dict:
        """
        解析 extends 继承，合并父子配置。

        Args:
            registry: 所有已知工作流配置 {name: config}
        """
        parent_name = self.config.get("extends")
        if not parent_name:
            return dict(self.config)

        parent = registry.get(parent_name)
        if not parent:
            logger.warning(f"extends 引用的父配置不存在: {parent_name}")
            return dict(self.config)

        # 递归解析父配置的 extends
        parent_engine = DeclarativeEngine(parent)
        resolved_parent = parent_engine.resolve_extends(registry)

        merged: Dict[str, Any] = {**resolved_parent}
        merged["name"] = self.config["name"]
        merged["description"] = self.config.get("description", resolved_parent.get("description", ""))

        # default_style 浅合并
        merged["default_style"] = {
            **resolved_parent.get("default_style", {}),
            **self.config.get("default_style", {}),
        }

        # phases 按 key 覆盖
        merged["phases"] = {**resolved_parent.get("phases", {})}
        for key, val in self.config.get("phases", {}).items():
            merged["phases"][key] = val

        # layers 按 key 覆盖
        merged["layers"] = {**resolved_parent.get("layers", {})}
        for key, val in self.config.get("layers", {}).items():
            merged["layers"][key] = val

        return merged
