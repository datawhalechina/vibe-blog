"""
BlogMemoryConfig — 博客记忆系统配置（Pydantic 校验版）

借鉴 DeerFlow MemoryConfig 的 Pydantic 校验模式，
适配 vibe-blog 多用户博客生成场景。
"""

import os
from pydantic import BaseModel, Field


class BlogMemoryConfig(BaseModel):
    """博客记忆系统配置 — Pydantic 校验版"""

    enabled: bool = Field(default=True, description="记忆系统总开关")
    storage_backend: str = Field(default="json", description="存储后端类型 (json | sqlite)")
    storage_path: str = Field(default="data/memory/", description="记忆文件存储目录")
    debounce_seconds: int = Field(default=10, ge=1, le=300, description="去抖等待秒数")
    model_name: str | None = Field(default=None, description="记忆更新用 LLM 模型名")
    max_facts: int = Field(default=200, ge=10, le=1000, description="单用户事实存储上限")
    fact_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="事实最低置信度阈值")
    injection_enabled: bool = Field(default=True, description="是否将记忆注入 system prompt")
    max_injection_tokens: int = Field(default=1500, ge=100, le=8000, description="记忆注入最大 token 数")
    auto_extract_enabled: bool = Field(default=True, description="LLM 自动记忆提取开关")

    @classmethod
    def from_env(cls) -> "BlogMemoryConfig":
        """从环境变量加载配置"""
        return cls(
            enabled=os.getenv("MEMORY_ENABLED", "true").lower() == "true",
            storage_path=os.getenv("MEMORY_STORAGE_PATH", "data/memory/"),
            debounce_seconds=int(os.getenv("MEMORY_DEBOUNCE_SECONDS", "10")),
            model_name=os.getenv("MEMORY_MODEL_NAME") or None,
            max_facts=int(os.getenv("MEMORY_MAX_FACTS", "200")),
            fact_confidence_threshold=float(os.getenv("MEMORY_FACT_THRESHOLD", "0.7")),
            injection_enabled=os.getenv("MEMORY_INJECTION_ENABLED", "true").lower() == "true",
            max_injection_tokens=int(os.getenv("MEMORY_MAX_INJECTION_TOKENS", "1500")),
            auto_extract_enabled=os.getenv("MEMORY_AUTO_EXTRACT_ENABLED", "true").lower() == "true",
        )


# ── 全局单例 ──

_memory_config: BlogMemoryConfig = BlogMemoryConfig()


def get_memory_config() -> BlogMemoryConfig:
    """获取当前记忆配置（全局单例）"""
    return _memory_config


def set_memory_config(config: BlogMemoryConfig) -> None:
    """设置记忆配置"""
    global _memory_config
    _memory_config = config


def load_memory_config_from_env() -> None:
    """从环境变量加载并设置全局配置"""
    global _memory_config
    _memory_config = BlogMemoryConfig.from_env()
