"""
37.14 Skill 注册中心

SkillRegistry — 装饰器注册 + 发现机制。
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillDefinition:
    name: str
    description: str
    func: Callable
    input_type: str
    output_type: str
    post_process: bool = False
    auto_run: bool = False
    timeout: int = 60


class SkillRegistry:
    """Skill 注册中心"""

    _skills: Dict[str, SkillDefinition] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        input_type: str,
        output_type: str,
        post_process: bool = False,
        auto_run: bool = False,
        timeout: int = 60,
    ):
        """装饰器：注册一个 Skill"""
        def decorator(func: Callable) -> Callable:
            cls._skills[name] = SkillDefinition(
                name=name,
                description=description,
                func=func,
                input_type=input_type,
                output_type=output_type,
                post_process=post_process,
                auto_run=auto_run,
                timeout=timeout,
            )
            logger.debug(f"Skill 已注册: {name}")
            return func
        return decorator

    @classmethod
    def get_all_skills(cls) -> List[SkillDefinition]:
        return list(cls._skills.values())

    @classmethod
    def get_skill(cls, name: str) -> Optional[SkillDefinition]:
        return cls._skills.get(name)

    @classmethod
    def get_post_process_skills(cls, auto_only: bool = True) -> List[SkillDefinition]:
        skills = [s for s in cls._skills.values() if s.post_process]
        if auto_only:
            skills = [s for s in skills if s.auto_run]
        return skills
