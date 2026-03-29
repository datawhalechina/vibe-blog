"""
37.12 YAML → JSON 迁移工具

将现有 6 套 YAML 预设 + agent_registry.yaml 一次性迁移为 JSON 格式。
"""
import json
import logging
import os
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


def migrate_yaml_to_json(yaml_path: str) -> dict:
    """将单个 YAML 文件转换为 JSON 兼容的 dict"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def migrate_all_presets(configs_dir: str, output_dir: str) -> List[str]:
    """
    批量迁移目录下所有 YAML 文件为 JSON。

    Returns:
        迁移成功的文件名列表（不含扩展名）
    """
    os.makedirs(output_dir, exist_ok=True)
    migrated: List[str] = []

    for filename in sorted(os.listdir(configs_dir)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        yaml_path = os.path.join(configs_dir, filename)
        name = os.path.splitext(filename)[0]
        try:
            data = migrate_yaml_to_json(yaml_path)
            json_path = os.path.join(output_dir, f"{name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            migrated.append(name)
            logger.info(f"迁移成功: {filename} → {name}.json")
        except Exception as e:
            logger.error(f"迁移失败: {filename}: {e}")

    return migrated
