"""
BlogMemoryConfig — 博客记忆系统配置（102.03）
"""

import os
from dataclasses import dataclass, field


@dataclass
class BlogMemoryConfig:
    """博客记忆系统配置"""
    enabled: bool = True
    storage_backend: str = "json"       # json | sqlite（预留）
    storage_path: str = "data/memory/"
    debounce_seconds: int = 10
    max_facts: int = 200
    fact_confidence_threshold: float = 0.7
    injection_enabled: bool = True
    max_injection_tokens: int = 1500
    auto_extract_enabled: bool = True   # LLM 自动记忆提取开关
    model_name: str = ""                # 记忆提取使用的模型（空=默认模型）

    @classmethod
    def from_env(cls) -> "BlogMemoryConfig":
        """从环境变量加载配置"""
        return cls(
            enabled=os.getenv("MEMORY_ENABLED", "true").lower() == "true",
            storage_path=os.getenv("MEMORY_STORAGE_PATH", "data/memory/"),
            debounce_seconds=int(os.getenv("MEMORY_DEBOUNCE_SECONDS", "10")),
            max_facts=int(os.getenv("MEMORY_MAX_FACTS", "200")),
            fact_confidence_threshold=float(os.getenv("MEMORY_FACT_THRESHOLD", "0.7")),
            injection_enabled=os.getenv("MEMORY_INJECTION_ENABLED", "true").lower() == "true",
            max_injection_tokens=int(os.getenv("MEMORY_MAX_INJECTION_TOKENS", "1500")),
            auto_extract_enabled=os.getenv("MEMORY_AUTO_EXTRACT_ENABLED", "true").lower() == "true",
            model_name=os.getenv("MEMORY_MODEL_NAME", ""),
        )
