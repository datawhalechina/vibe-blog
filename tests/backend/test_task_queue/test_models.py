"""
test_models.py — Pydantic 数据模型单元测试 (M1-M8)
"""
import pytest
from datetime import datetime

from services.task_queue.models import (
    BlogTask, BlogGenerationConfig, TriggerConfig, PublishConfig,
    ExecutionRecord, SchedulerConfig,
    QueueStatus, TaskPriority, TriggerType,
)


class TestBlogTask:
    """M1-M4: BlogTask 模型测试"""

    def test_m1_default_values(self):
        """M1: 默认值正确"""
        task = BlogTask(name="测试", generation=BlogGenerationConfig(topic="AI"))
        assert task.status == QueueStatus.QUEUED
        assert task.priority == TaskPriority.NORMAL
        assert task.progress == 0
        assert task.trigger.type == TriggerType.MANUAL
        assert task.publish.auto_publish is False
        assert len(task.id) == 8
        assert isinstance(task.created_at, datetime)

    def test_m2_custom_priority(self):
        """M2: 自定义优先级"""
        task = BlogTask(
            name="高优", generation=BlogGenerationConfig(topic="AI"),
            priority=TaskPriority.HIGH,
        )
        assert task.priority == TaskPriority.HIGH
        assert task.priority.value == 10

    def test_m3_unique_ids(self):
        """M3: 每个任务 ID 唯一"""
        tasks = [
            BlogTask(name=f"t{i}", generation=BlogGenerationConfig(topic="AI"))
            for i in range(10)
        ]
        ids = {t.id for t in tasks}
        assert len(ids) == 10

    def test_m4_serialization_roundtrip(self):
        """M4: JSON 序列化/反序列化"""
        task = BlogTask(
            name="序列化测试",
            generation=BlogGenerationConfig(topic="LLM", article_type="deep-dive"),
            priority=TaskPriority.HIGH,
            tags=["test", "ai"],
        )
        json_str = task.model_dump_json()
        restored = BlogTask.model_validate_json(json_str)
        assert restored.name == task.name
        assert restored.generation.topic == "LLM"
        assert restored.priority == TaskPriority.HIGH
        assert restored.tags == ["test", "ai"]


class TestTriggerConfig:
    """M5-M6: TriggerConfig 测试"""

    def test_m5_cron_trigger(self):
        """M5: Cron 触发配置"""
        trigger = TriggerConfig(
            type=TriggerType.CRON,
            cron_expression="0 8 * * 1-5",
            human_readable="每个工作日早上8点",
        )
        assert trigger.type == TriggerType.CRON
        assert trigger.cron_expression == "0 8 * * 1-5"
        assert trigger.timezone == "Asia/Shanghai"

    def test_m6_once_trigger(self):
        """M6: 一次性触发配置"""
        target = datetime(2026, 3, 1, 15, 0)
        trigger = TriggerConfig(
            type=TriggerType.ONCE,
            scheduled_at=target,
        )
        assert trigger.type == TriggerType.ONCE
        assert trigger.scheduled_at == target


class TestExecutionRecord:
    """M7: ExecutionRecord 测试"""

    def test_m7_execution_record(self):
        """M7: 执行记录创建"""
        record = ExecutionRecord(
            task_id="abc123",
            task_name="测试任务",
            status=QueueStatus.COMPLETED,
            started_at=datetime(2026, 1, 1, 10, 0),
            completed_at=datetime(2026, 1, 1, 10, 5),
            duration_ms=300000,
            output_url="/blog/test-1",
        )
        assert record.task_id == "abc123"
        assert record.duration_ms == 300000
        assert record.published is False


class TestSchedulerConfig:
    """M8: SchedulerConfig 测试"""

    def test_m8_defaults(self):
        """M8: 全局配置默认值"""
        config = SchedulerConfig()
        assert config.max_concurrent_tasks == 2
        assert config.default_timeout == 1800
        assert config.default_timezone == "Asia/Shanghai"
