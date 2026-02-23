"""
统一技能数据模型

合并 SkillDefinition（装饰器注册）和 WritingSkill（SKILL.md 声明式）
为单一 UnifiedSkill 类型，支持两种来源的技能统一管理。
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional


class SkillSource(str, Enum):
    """技能来源类型"""
    DECLARATIVE = "declarative"    # SKILL.md 声明式
    PROGRAMMATIC = "programmatic"  # 装饰器注册


class SkillCategory(str, Enum):
    """技能分类"""
    PUBLIC = "public"
    CUSTOM = "custom"
    BUILTIN = "builtin"  # 代码内置的后处理技能


@dataclass
class UnifiedSkill:
    """统一技能数据结构"""
    name: str
    description: str
    source: SkillSource
    category: SkillCategory = SkillCategory.PUBLIC
    enabled: bool = True

    # SKILL.md 声明式字段
    license: Optional[str] = None
    skill_dir: Optional[Path] = None
    skill_file: Optional[Path] = None
    allowed_tools: List[str] = field(default_factory=list)
    content: str = ""

    # 装饰器注册字段
    func: Optional[Callable] = None
    input_type: str = ""
    output_type: str = ""
    post_process: bool = False
    auto_run: bool = False
    timeout: int = 60
