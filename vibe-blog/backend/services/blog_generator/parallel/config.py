"""并行任务配置"""

from dataclasses import dataclass


@dataclass
class TaskConfig:
    """并行任务配置"""
    name: str                          # 任务名称（用于日志和追踪）
    timeout_seconds: int = 300         # 单任务超时（秒），默认 5 分钟
    max_retries: int = 0              # 最大重试次数
    fallback_to_original: bool = True  # 失败时是否回退到原始内容
