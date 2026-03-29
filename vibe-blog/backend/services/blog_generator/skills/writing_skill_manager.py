"""
WritingSkillManager — SKILL.md 声明式写作技能管理器（102.06）

借鉴 DeerFlow 的 SKILL.md 格式和 loader.py 加载机制，
为 VibeBlog 提供声明式写作方法论管理。

与现有 SkillRegistry（装饰器注册的后处理技能）互补：
- SkillRegistry: flashcard / mindmap / study_note 等后处理技能
- WritingSkillManager: 写作方法论技能，注入系统提示词指导写作过程
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WritingSkill:
    """写作技能数据结构"""
    name: str
    description: str
    license: Optional[str]
    skill_dir: Path
    skill_file: Path
    category: str           # 'public' | 'custom'
    enabled: bool = True
    allowed_tools: List[str] = field(default_factory=list)
    content: str = ""       # SKILL.md 正文（方法论部分）


def parse_skill_md(skill_file: Path, category: str) -> Optional[WritingSkill]:
    """解析 SKILL.md（YAML frontmatter + Markdown 正文）"""
    if not skill_file.exists() or skill_file.name != "SKILL.md":
        return None
    try:
        raw = skill_file.read_text(encoding="utf-8")
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        if not fm_match:
            return None

        metadata = {}
        for line in fm_match.group(1).split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        name = metadata.get("name")
        description = metadata.get("description")
        if not name or not description:
            return None

        allowed_tools_str = metadata.get("allowed-tools", "")
        allowed_tools = [t.strip() for t in allowed_tools_str.split(",") if t.strip()]

        body = raw[fm_match.end():]

        return WritingSkill(
            name=name,
            description=description,
            license=metadata.get("license"),
            skill_dir=skill_file.parent,
            skill_file=skill_file,
            category=category,
            allowed_tools=allowed_tools,
            content=body,
        )
    except Exception as e:
        logger.error(f"解析 SKILL.md 失败 {skill_file}: {e}")
        return None


class WritingSkillManager:
    """
    写作技能管理器

    扫描 skills/{public,custom}/ 目录，加载 SKILL.md，
    按主题/文章类型匹配最佳技能，注入到 Agent 系统提示词。
    """

    def __init__(self, skills_root: Optional[Path] = None):
        self._skills_root = skills_root or self._default_root()
        self._skills: List[WritingSkill] = []
        self._loaded = False

    @staticmethod
    def _default_root() -> Path:
        return Path(__file__).resolve().parent.parent.parent.parent / "skills"

    def load(self, enabled_only: bool = True) -> List[WritingSkill]:
        """扫描并加载所有技能"""
        self._skills = []
        for category in ("public", "custom"):
            cat_dir = self._skills_root / category
            if not cat_dir.is_dir():
                continue
            for skill_dir in sorted(cat_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                skill = parse_skill_md(skill_file, category)
                if skill:
                    self._skills.append(skill)

        if enabled_only:
            self._skills = [s for s in self._skills if s.enabled]

        self._skills.sort(key=lambda s: s.name)
        self._loaded = True
        logger.info(f"加载 {len(self._skills)} 个写作技能")
        return self._skills

    def match_skill(self, topic: str, article_type: str = "") -> Optional[WritingSkill]:
        """根据主题和文章类型匹配最佳技能"""
        if not self._loaded:
            self.load()

        for skill in self._skills:
            desc_lower = skill.description.lower()
            if article_type and article_type.lower() in desc_lower:
                return skill
            if any(kw in topic.lower() for kw in skill.name.split("-") if len(kw) > 2):
                return skill

        return next((s for s in self._skills if s.name == "deep-research"), None)

    def build_system_prompt_section(self, skill: WritingSkill) -> str:
        """将技能内容格式化为系统提示词片段"""
        return (
            f'\n<writing-skill name="{skill.name}">\n'
            f"{skill.content}\n"
            f"</writing-skill>\n"
        )

    def list_skills(self) -> List[WritingSkill]:
        if not self._loaded:
            self.load()
        return self._skills
