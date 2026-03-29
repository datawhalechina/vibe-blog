"""
StyleProfile — 工作流风格配置

行为参数：收拢散落的 if target_length 逻辑（44处 → 统一配置）
风格参数：文风、配图、AI 特性开关
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, List


@dataclass
class StyleProfile:
    """
    用户风格配置 — 工作流是"骨架"，风格是"皮肤"
    """

    # === 行为参数（收拢 44 处 if/else）===

    max_revision_rounds: int = 3
    """最大修订轮数（mini/short=1, medium=3, long=5）"""

    max_questioning_rounds: int = 2
    """最大追问轮数（mini/short=1, medium=2, long=3）"""

    revision_strategy: Literal["correct_only", "full_revise"] = "full_revise"
    """修订策略：correct_only=只更正不扩展, full_revise=完整修订"""

    revision_severity_filter: Literal["high_only", "all"] = "all"
    """修订问题过滤：high_only=只处理high, all=处理所有"""

    depth_requirement: Literal["minimal", "shallow", "medium", "deep"] = "medium"
    """追问深度要求"""

    enable_knowledge_refinement: bool = True
    """是否启用知识增强搜索"""

    image_generation_mode: Literal["mini_section", "full"] = "full"
    """配图生成模式：mini_section=章节配图, full=完整配图"""

    # === 风格参数 ===

    tone: str = "professional"
    complexity: str = "intermediate"
    verbosity: str = "balanced"

    # === 配图参数 ===

    image_style: str = ""
    """配图风格 ID（空=使用前端传入值）"""

    # === 增强 Agent 开关 ===

    enable_fact_check: bool = False
    enable_thread_check: bool = True
    enable_voice_check: bool = True
    enable_humanizer: bool = True
    enable_text_cleanup: bool = True
    enable_summary_gen: bool = True

    # === 搜索增强参数（71 号方案）===

    enable_ai_boost: bool = True
    """AI 话题自动增强搜索（自动扩展到所有 AI 权威博客源）"""

    enable_parallel: bool = True
    """是否启用并行执行（默认开启，调试/追踪时可关闭）"""

    # === 41.10 动态 Agent 角色 ===

    persona_key: str = ""
    """预设人设 key（如 'tech_expert'），留空不注入人设"""

    # === 41.11 Guidelines 驱动审核 ===

    review_guidelines: List[str] = None
    """自定义审核标准列表，None 使用默认审核维度"""

    def get_persona_prompt(self) -> str:
        """获取人设 Prompt 片段（41.10）"""
        if not self.persona_key:
            return ""
        import os
        if os.environ.get('AGENT_PERSONA_ENABLED', 'false').lower() != 'true':
            return ""
        from .persona_presets import get_persona
        persona = get_persona(self.persona_key)
        return persona.to_prompt_segment() if persona else ""

    # === 预设套餐 ===

    @classmethod
    def mini(cls) -> 'StyleProfile':
        return cls(
            max_revision_rounds=1,
            max_questioning_rounds=1,
            revision_strategy="correct_only",
            revision_severity_filter="high_only",
            depth_requirement="minimal",
            enable_knowledge_refinement=False,
            image_generation_mode="mini_section",
            tone="casual", complexity="beginner", verbosity="concise",
            enable_fact_check=False, enable_thread_check=False,
            enable_voice_check=False, enable_humanizer=False,
            enable_text_cleanup=True, enable_summary_gen=False,
            enable_ai_boost=False,
        )

    @classmethod
    def short(cls) -> 'StyleProfile':
        return cls(
            max_revision_rounds=1,
            max_questioning_rounds=1,
            revision_strategy="correct_only",
            revision_severity_filter="high_only",
            depth_requirement="shallow",
            enable_knowledge_refinement=False,
            image_generation_mode="mini_section",
            tone="professional", complexity="intermediate", verbosity="concise",
            enable_humanizer=True, enable_text_cleanup=True,
            enable_summary_gen=True,
        )

    @classmethod
    def medium(cls) -> 'StyleProfile':
        return cls(
            max_revision_rounds=3,
            max_questioning_rounds=2,
            revision_strategy="full_revise",
            revision_severity_filter="all",
            depth_requirement="medium",
            enable_knowledge_refinement=True,
            image_generation_mode="full",
            tone="professional", complexity="intermediate", verbosity="balanced",
            enable_thread_check=True, enable_humanizer=True,
            enable_text_cleanup=True, enable_summary_gen=True,
        )

    @classmethod
    def long(cls) -> 'StyleProfile':
        return cls(
            max_revision_rounds=5,
            max_questioning_rounds=3,
            revision_strategy="full_revise",
            revision_severity_filter="all",
            depth_requirement="deep",
            enable_knowledge_refinement=True,
            image_generation_mode="full",
            tone="professional", complexity="advanced", verbosity="detailed",
            enable_fact_check=True, enable_thread_check=True,
            enable_voice_check=True, enable_humanizer=True,
            enable_text_cleanup=True, enable_summary_gen=True,
        )

    @classmethod
    def deep_analysis(cls) -> 'StyleProfile':
        return cls(
            max_revision_rounds=5,
            revision_strategy="full_revise",
            revision_severity_filter="all",
            depth_requirement="deep",
            enable_knowledge_refinement=True,
            image_generation_mode="full",
            tone="academic", complexity="advanced", verbosity="detailed",
            enable_fact_check=True, enable_thread_check=True,
            enable_voice_check=True, enable_humanizer=True,
            enable_text_cleanup=True, enable_summary_gen=True,
        )

    @classmethod
    def science_popular(cls) -> 'StyleProfile':
        return cls(
            max_revision_rounds=3,
            depth_requirement="medium",
            enable_knowledge_refinement=True,
            tone="casual", complexity="beginner", verbosity="balanced",
            image_style="watercolor",
            enable_humanizer=True,
        )

    @classmethod
    def from_target_length(cls, target_length: str) -> 'StyleProfile':
        """从 target_length 映射到预设（向后兼容）"""
        presets = {
            'mini': cls.mini,
            'short': cls.short,
            'medium': cls.medium,
            'long': cls.long,
            'custom': cls.medium,
        }
        factory = presets.get(target_length, cls.medium)
        return factory()
