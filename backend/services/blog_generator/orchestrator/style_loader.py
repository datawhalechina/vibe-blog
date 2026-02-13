"""
37.13 写作模板体系 — StyleLoader

加载、校验、CRUD 管理 Style JSON 文件。
"""
import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StyleLoader:
    """Style 加载器"""

    def __init__(self, styles_dir: str = ""):
        if not styles_dir:
            backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            styles_dir = os.path.join(backend, "workflow_configs", "styles")
        self.styles_dir = styles_dir
        self._cache: Dict[str, dict] = {}

    def load_all(self) -> Dict[str, dict]:
        """扫描目录加载所有 JSON 风格"""
        self._cache.clear()
        if not os.path.isdir(self.styles_dir):
            return self._cache
        for fname in os.listdir(self.styles_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.styles_dir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                name = data.get("name", fname.replace(".json", ""))
                self._cache[name] = data
            except Exception as e:
                logger.warning(f"加载风格失败 [{fname}]: {e}")
        return self._cache

    def get(self, name: str) -> Optional[dict]:
        """按名称获取风格"""
        if not self._cache:
            self.load_all()
        return self._cache.get(name)

    def save(self, style: dict) -> None:
        """校验并保存风格 JSON"""
        name = style.get("name")
        if not name:
            raise ValueError("风格必须包含 name 字段")
        os.makedirs(self.styles_dir, exist_ok=True)
        path = os.path.join(self.styles_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(style, f, ensure_ascii=False, indent=2)
        self._cache[name] = style

    def delete(self, name: str) -> bool:
        """删除风格（预置不可删）"""
        s = self.get(name)
        if s and s.get("builtin"):
            raise PermissionError(f"预置风格 '{name}' 不可删除")
        path = os.path.join(self.styles_dir, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            self._cache.pop(name, None)
            return True
        return False
