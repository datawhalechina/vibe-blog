"""
统一技能加载器

扫描 SKILL.md 声明式技能 + 读取 SkillRegistry 装饰器注册技能，
合并为统一的 UnifiedSkill 列表，支持 skills_config.json 启用/禁用管理
和 ZIP 归档安装自定义技能。
"""
import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from .registry import SkillRegistry
from .skills_state_config import SkillsStateConfig
from .unified_skill import SkillCategory, SkillSource, UnifiedSkill
from .writing_skill_manager import parse_skill_md

logger = logging.getLogger(__name__)

# SKILL.md name 验证: hyphen-case
_HYPHEN_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# frontmatter 白名单
_ALLOWED_FM_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
_MAX_NAME_LEN = 64
_MAX_DESC_LEN = 1024


def _default_skills_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "skills"


class UnifiedSkillLoader:
    """统一技能加载器"""

    def __init__(
        self,
        skills_root: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ):
        self._skills_root = skills_root or _default_skills_root()
        self._config = SkillsStateConfig(config_path=config_path)
        self._skills: List[UnifiedSkill] = []
        self._loaded = False

    def load(self, enabled_only: bool = True) -> List[UnifiedSkill]:
        """加载所有技能（声明式 + 装饰器注册）"""
        self._skills = []
        seen_names = set()

        # 1. 扫描 SKILL.md 声明式技能
        for category_str in ("public", "custom"):
            cat_dir = self._skills_root / category_str
            if not cat_dir.is_dir():
                continue
            category = (
                SkillCategory.PUBLIC
                if category_str == "public"
                else SkillCategory.CUSTOM
            )
            for skill_dir in sorted(cat_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                ws = parse_skill_md(skill_file, category_str)
                if ws is None:
                    continue
                us = UnifiedSkill(
                    name=ws.name,
                    description=ws.description,
                    source=SkillSource.DECLARATIVE,
                    category=category,
                    enabled=self._config.is_enabled(ws.name),
                    license=ws.license,
                    skill_dir=ws.skill_dir,
                    skill_file=ws.skill_file,
                    allowed_tools=ws.allowed_tools,
                    content=ws.content,
                )
                self._skills.append(us)
                seen_names.add(us.name)

        # 2. 读取 SkillRegistry 装饰器注册的技能
        for defn in SkillRegistry.get_all_skills():
            if defn.name in seen_names:
                continue
            us = UnifiedSkill(
                name=defn.name,
                description=defn.description,
                source=SkillSource.PROGRAMMATIC,
                category=SkillCategory.BUILTIN,
                enabled=self._config.is_enabled(defn.name),
                func=defn.func,
                input_type=defn.input_type,
                output_type=defn.output_type,
                post_process=defn.post_process,
                auto_run=defn.auto_run,
                timeout=defn.timeout,
            )
            self._skills.append(us)
            seen_names.add(us.name)

        # 3. 过滤 + 排序
        if enabled_only:
            self._skills = [s for s in self._skills if s.enabled]
        self._skills.sort(key=lambda s: s.name)
        self._loaded = True
        logger.info(f"加载 {len(self._skills)} 个统一技能")
        return self._skills

    def get_skill(self, name: str) -> Optional[UnifiedSkill]:
        """按名称获取技能"""
        if not self._loaded:
            self.load(enabled_only=False)
        return next((s for s in self._skills if s.name == name), None)

    def list_skills(self) -> List[UnifiedSkill]:
        """列出所有已加载技能"""
        if not self._loaded:
            self.load(enabled_only=False)
        return list(self._skills)

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """设置技能启用状态"""
        skill = self.get_skill(name)
        if skill is None:
            return False
        skill.enabled = enabled
        self._config.set_enabled(name, enabled)
        return True

    def install_from_zip(self, zip_path: Path) -> Dict:
        """从 .skill ZIP 归档安装自定义技能"""
        if not zip_path.exists():
            return {"success": False, "skill_name": "", "message": "文件不存在"}
        if not zipfile.is_zipfile(zip_path):
            return {"success": False, "skill_name": "", "message": "不是有效的 ZIP 归档"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(tmp)
            except Exception as e:
                return {"success": False, "skill_name": "", "message": f"解压失败: {e}"}

            # 查找 SKILL.md
            skill_md = self._find_skill_md(tmp)
            if skill_md is None:
                return {"success": False, "skill_name": "", "message": "ZIP 中未找到 SKILL.md"}

            # 验证 frontmatter
            validation = self._validate_frontmatter(skill_md)
            if not validation["valid"]:
                return {"success": False, "skill_name": validation.get("name", ""), "message": validation["error"]}

            skill_name = validation["name"]

            # 检查冲突
            target = self._skills_root / "custom" / skill_name
            if target.exists():
                return {"success": False, "skill_name": skill_name, "message": f"技能 '{skill_name}' 已存在"}

            # 复制到 custom 目录
            source_dir = skill_md.parent
            target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, target, dirs_exist_ok=True)

            # 重新加载
            self._loaded = False
            return {"success": True, "skill_name": skill_name, "message": f"技能 '{skill_name}' 安装成功"}

    @staticmethod
    def _find_skill_md(root: Path) -> Optional[Path]:
        """在解压目录中查找 SKILL.md"""
        # 直接在根目录
        if (root / "SKILL.md").exists():
            return root / "SKILL.md"
        # 在子目录中
        for child in root.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                return child / "SKILL.md"
        return None

    @staticmethod
    def _validate_frontmatter(skill_md: Path) -> Dict:
        """验证 SKILL.md frontmatter"""
        try:
            raw = skill_md.read_text(encoding="utf-8")
        except Exception as e:
            return {"valid": False, "error": f"读取失败: {e}"}

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        if not fm_match:
            return {"valid": False, "error": "缺少 YAML frontmatter"}

        metadata = {}
        for line in fm_match.group(1).split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        name = metadata.get("name", "")
        description = metadata.get("description", "")

        if not name:
            return {"valid": False, "error": "缺少 name 字段"}
        if not description:
            return {"valid": False, "error": "缺少 description 字段", "name": name}
        if not _HYPHEN_CASE_RE.match(name):
            return {"valid": False, "error": f"name 必须为 hyphen-case: {name}", "name": name}
        if len(name) > _MAX_NAME_LEN:
            return {"valid": False, "error": f"name 超过 {_MAX_NAME_LEN} 字符", "name": name}
        if len(description) > _MAX_DESC_LEN:
            return {"valid": False, "error": f"description 超过 {_MAX_DESC_LEN} 字符", "name": name}
        if "<" in description or ">" in description:
            return {"valid": False, "error": "description 不允许包含尖括号", "name": name}

        # 检查未知 frontmatter 键
        unknown = set(metadata.keys()) - _ALLOWED_FM_KEYS
        if unknown:
            return {"valid": False, "error": f"未知 frontmatter 字段: {unknown}", "name": name}

        return {"valid": True, "name": name, "description": description}

    @property
    def config(self) -> SkillsStateConfig:
        return self._config
