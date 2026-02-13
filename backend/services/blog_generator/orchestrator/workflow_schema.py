"""
37.12 工作流 JSON Schema 校验
"""
from typing import List


def validate_workflow_config(config: dict) -> List[str]:
    """
    校验工作流 JSON 配置的基本结构。

    Returns:
        错误列表，空列表表示校验通过
    """
    errors: List[str] = []

    if not isinstance(config, dict):
        return ["config 必须是 dict"]

    if "name" not in config:
        errors.append("缺少必填字段: name")
    elif not isinstance(config["name"], str):
        errors.append("name 必须是字符串")

    if "phases" in config:
        if not isinstance(config["phases"], dict):
            errors.append("phases 必须是 dict")
        else:
            for phase_name, agents in config["phases"].items():
                if not isinstance(agents, list):
                    errors.append(f"phases.{phase_name} 必须是列表")

    if "default_style" in config and not isinstance(config["default_style"], dict):
        errors.append("default_style 必须是 dict")

    if "layers" in config:
        if not isinstance(config["layers"], dict):
            errors.append("layers 必须是 dict")
        else:
            for layer_name, layer_cfg in config["layers"].items():
                if not isinstance(layer_cfg, dict):
                    errors.append(f"layers.{layer_name} 必须是 dict")
                    continue
                has_pipeline = "pipeline" in layer_cfg
                has_parallel = "parallel" in layer_cfg
                if has_pipeline and has_parallel:
                    errors.append(f"layers.{layer_name} 不能同时有 pipeline 和 parallel")

    return errors
