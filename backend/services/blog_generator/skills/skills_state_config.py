"""
技能状态配置管理

读写 skills_config.json，管理技能启用/禁用状态。
文件不存在或解析失败时默认全部启用。
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _default_config_path() -> Path:
    """默认配置文件路径: backend/skills_config.json"""
    return Path(__file__).resolve().parent.parent.parent.parent / "skills_config.json"


class SkillsStateConfig:
    """技能启用/禁用状态配置"""

    def __init__(self, config_path: Optional[Path] = None):
        self._path = config_path or _default_config_path()
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        """从 JSON 文件加载配置"""
        if not self._path.exists():
            logger.debug(f"skills_config.json 不存在: {self._path}，使用默认值")
            self._data = {}
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._data = raw.get("skills", {})
        except Exception as e:
            logger.warning(f"skills_config.json 解析失败: {e}，使用默认值")
            self._data = {}

    def is_enabled(self, skill_name: str) -> bool:
        """查询技能是否启用（默认启用）"""
        entry = self._data.get(skill_name)
        if entry is None:
            return True
        return entry.get("enabled", True)

    def set_enabled(self, skill_name: str, enabled: bool):
        """设置技能启用状态并持久化"""
        self._data.setdefault(skill_name, {})["enabled"] = enabled
        self._save()

    def _save(self):
        """持久化到 JSON 文件"""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"skills": self._data}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"skills_config.json 写入失败: {e}")

    def get_all(self) -> Dict[str, dict]:
        """返回所有配置条目"""
        return dict(self._data)

    def reload(self):
        """重新加载配置"""
        self._load()
