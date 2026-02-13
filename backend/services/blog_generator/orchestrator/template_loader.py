"""
37.13 写作模板体系 — TemplateLoader

加载、校验、CRUD 管理 WritingTemplate JSON 文件。
"""
import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TemplateLoader:
    """WritingTemplate 加载器"""

    def __init__(self, templates_dir: str = ""):
        if not templates_dir:
            backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            templates_dir = os.path.join(backend, "workflow_configs", "templates")
        self.templates_dir = templates_dir
        self._cache: Dict[str, dict] = {}

    def load_all(self) -> Dict[str, dict]:
        """扫描目录加载所有 JSON 模板"""
        self._cache.clear()
        if not os.path.isdir(self.templates_dir):
            return self._cache
        for fname in os.listdir(self.templates_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.templates_dir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("name", fname.replace(".json", ""))
                self._cache[name] = data
            except Exception as e:
                logger.warning(f"加载模板失败 [{fname}]: {e}")
        return self._cache

    def get(self, name: str) -> Optional[dict]:
        """按名称获取模板"""
        if not self._cache:
            self.load_all()
        return self._cache.get(name)

    def save(self, template: dict) -> None:
        """校验并保存模板 JSON"""
        name = template.get("name")
        if not name:
            raise ValueError("模板必须包含 name 字段")
        os.makedirs(self.templates_dir, exist_ok=True)
        path = os.path.join(self.templates_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        self._cache[name] = template

    def delete(self, name: str) -> bool:
        """删除模板（预置不可删）"""
        tpl = self.get(name)
        if tpl and tpl.get("builtin"):
            raise PermissionError(f"预置模板 '{name}' 不可删除")
        path = os.path.join(self.templates_dir, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            self._cache.pop(name, None)
            return True
        return False
