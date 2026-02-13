"""
task_queue 数据模型 — Pydantic v2

核心模型：
- BlogTask: 博客生成任务（排队/执行/结果）
- TriggerConfig: 触发配置（手动/Cron/一次性）
- BlogGenerationConfig: 生成参数
- PublishConfig: 发布配置
- ExecutionRecord: 执行历史记录
- SchedulerConfig: 全局调度配置
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    MANUAL = "manual"
    CRON = "cron"
    ONCE = "once"


class QueueStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 10


class TriggerConfig(BaseModel):
    type: TriggerType = TriggerType.MANUAL
    cron_expression: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    timezone: str = "Asia/Shanghai"
    human_readable: Optional[str] = None


class BlogGenerationConfig(BaseModel):
    topic: str
    article_type: str = "tutorial"
    target_length: str = "medium"
    image_style: Optional[str] = None
    generate_cover_video: bool = False
    custom_sections: Optional[int] = None
    custom_images: Optional[int] = None
    custom_code_blocks: Optional[int] = None
    custom_word_count: Optional[int] = None


class PublishConfig(BaseModel):
    auto_publish: bool = False
    platform: Optional[str] = None
    skip_quality_check: bool = False
    notify_on_complete: bool = True
    notify_channel: Optional[str] = None


class BlogTask(BaseModel):
    """博客生成任务"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: Optional[str] = None

    trigger: TriggerConfig = Field(default_factory=TriggerConfig)
    generation: BlogGenerationConfig
    publish: PublishConfig = Field(default_factory=PublishConfig)

    status: QueueStatus = QueueStatus.QUEUED
    priority: TaskPriority = TaskPriority.NORMAL
    queue_position: Optional[int] = None

    # 进度
    progress: int = 0
    current_stage: str = ""
    stage_detail: str = ""

    # 结果
    output_url: Optional[str] = None
    output_word_count: Optional[int] = None
    output_image_count: Optional[int] = None

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    tags: list[str] = Field(default_factory=list)
    user_id: Optional[str] = None


class ExecutionRecord(BaseModel):
    """每次执行的历史记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    task_name: str

    status: QueueStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    triggered_by: str = "manual"

    output_url: Optional[str] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None

    published: bool = False
    publish_url: Optional[str] = None


class SchedulerConfig(BaseModel):
    """全局调度配置"""
    max_concurrent_tasks: int = 2
    default_timeout: int = 1800
    log_retention_days: int = 30
    max_execution_history: int = 100
    default_timezone: str = "Asia/Shanghai"
