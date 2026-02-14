"""
T2: Cron 数据模型测试
"""
import pytest
from datetime import datetime
from services.task_queue.models import (
    CronJob, CronJobState, CronSchedule, CronScheduleKind,
    CronJobStatus, BlogGenerationConfig,
)


class TestCronSchedule:
    def test_cron_schedule(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *")
        assert s.kind == CronScheduleKind.CRON
        assert s.expr == "0 8 * * *"
        assert s.tz == "Asia/Shanghai"

    def test_at_schedule(self):
        t = datetime(2025, 3, 1, 8, 0)
        s = CronSchedule(kind=CronScheduleKind.AT, at=t)
        assert s.at == t
        assert s.expr is None

    def test_every_schedule(self):
        s = CronSchedule(kind=CronScheduleKind.EVERY, every_seconds=3600)
        assert s.every_seconds == 3600
        assert s.anchor_at is None

    def test_every_with_anchor(self):
        anchor = datetime(2025, 1, 1, 0, 0)
        s = CronSchedule(
            kind=CronScheduleKind.EVERY,
            every_seconds=60,
            anchor_at=anchor,
        )
        assert s.anchor_at == anchor

    def test_custom_timezone(self):
        s = CronSchedule(
            kind=CronScheduleKind.CRON,
            expr="0 8 * * *",
            tz="America/New_York",
        )
        assert s.tz == "America/New_York"


class TestCronJobState:
    def test_defaults(self):
        state = CronJobState()
        assert state.consecutive_errors == 0
        assert state.schedule_error_count == 0
        assert state.running_at is None
        assert state.last_status is None
        assert state.next_run_at is None

    def test_with_values(self):
        state = CronJobState(
            consecutive_errors=3,
            last_status=CronJobStatus.ERROR,
            last_error="timeout",
        )
        assert state.consecutive_errors == 3
        assert state.last_status == CronJobStatus.ERROR


class TestCronJob:
    def test_defaults(self):
        job = CronJob(
            name="test",
            schedule=CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *"),
            generation=BlogGenerationConfig(topic="AI"),
        )
        assert job.enabled is True
        assert job.timeout_seconds == 600
        assert job.delete_after_run is False
        assert len(job.id) == 8
        assert job.state.consecutive_errors == 0
        assert job.tags == []

    def test_roundtrip_serialization(self):
        job = CronJob(
            name="test",
            schedule=CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *"),
            generation=BlogGenerationConfig(topic="AI"),
            tags=["daily", "ai"],
        )
        data = job.model_dump()
        restored = CronJob.model_validate(data)
        assert restored.name == job.name
        assert restored.schedule.expr == "0 8 * * *"
        assert restored.tags == ["daily", "ai"]
        assert restored.generation.topic == "AI"

    def test_json_roundtrip(self):
        job = CronJob(
            name="json-test",
            schedule=CronSchedule(kind=CronScheduleKind.AT, at=datetime(2025, 6, 1)),
            generation=BlogGenerationConfig(topic="test"),
        )
        json_str = job.model_dump_json()
        restored = CronJob.model_validate_json(json_str)
        assert restored.name == "json-test"
        assert restored.schedule.kind == CronScheduleKind.AT
