"""
T4: 调度计算 compute_next_run_at 测试
"""
import pytest
from datetime import datetime
from services.task_queue.models import CronSchedule, CronScheduleKind
from services.task_queue.cron_scheduler import compute_next_run_at


class TestAtSchedule:
    def test_future_at(self):
        s = CronSchedule(kind=CronScheduleKind.AT, at=datetime(2099, 1, 1))
        result = compute_next_run_at(s, datetime(2025, 1, 1))
        assert result == datetime(2099, 1, 1)

    def test_past_at(self):
        s = CronSchedule(kind=CronScheduleKind.AT, at=datetime(2020, 1, 1))
        result = compute_next_run_at(s, datetime(2025, 1, 1))
        assert result is None

    def test_at_none(self):
        s = CronSchedule(kind=CronScheduleKind.AT)
        assert compute_next_run_at(s, datetime(2025, 1, 1)) is None

    def test_at_equal_to_now(self):
        t = datetime(2025, 3, 1, 8, 0)
        s = CronSchedule(kind=CronScheduleKind.AT, at=t)
        # at == now → 应该返回 at（还没执行）
        result = compute_next_run_at(s, t)
        assert result == t


class TestEverySchedule:
    def test_before_anchor(self):
        anchor = datetime(2025, 3, 1, 12, 0)
        s = CronSchedule(
            kind=CronScheduleKind.EVERY, every_seconds=60, anchor_at=anchor
        )
        result = compute_next_run_at(s, datetime(2025, 3, 1, 11, 0))
        assert result == anchor

    def test_after_anchor_aligned(self):
        anchor = datetime(2025, 3, 1, 12, 0, 0)
        s = CronSchedule(
            kind=CronScheduleKind.EVERY, every_seconds=60, anchor_at=anchor
        )
        # now = 12:02:30 → next = 12:03:00
        result = compute_next_run_at(s, datetime(2025, 3, 1, 12, 2, 30))
        assert result == datetime(2025, 3, 1, 12, 3, 0)

    def test_hourly(self):
        anchor = datetime(2025, 3, 1, 8, 0, 0)
        s = CronSchedule(
            kind=CronScheduleKind.EVERY, every_seconds=3600, anchor_at=anchor
        )
        # now = 10:30 → next = 11:00
        result = compute_next_run_at(s, datetime(2025, 3, 1, 10, 30, 0))
        assert result == datetime(2025, 3, 1, 11, 0, 0)

    def test_no_anchor_uses_now(self):
        s = CronSchedule(kind=CronScheduleKind.EVERY, every_seconds=60)
        now = datetime(2025, 3, 1, 12, 0, 0)
        result = compute_next_run_at(s, now)
        assert result is not None
        assert result > now
        # 无 anchor 时，next = now + every_seconds
        assert result == datetime(2025, 3, 1, 12, 1, 0)

    def test_every_seconds_none(self):
        s = CronSchedule(kind=CronScheduleKind.EVERY)
        assert compute_next_run_at(s, datetime(2025, 1, 1)) is None

    def test_exactly_on_anchor(self):
        anchor = datetime(2025, 3, 1, 12, 0, 0)
        s = CronSchedule(
            kind=CronScheduleKind.EVERY, every_seconds=60, anchor_at=anchor
        )
        # now == anchor → next = anchor + 60s
        result = compute_next_run_at(s, anchor)
        assert result == datetime(2025, 3, 1, 12, 1, 0)


class TestCronSchedule:
    def test_daily_8am(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *")
        now = datetime(2025, 3, 1, 7, 0, 0)
        result = compute_next_run_at(s, now)
        assert result == datetime(2025, 3, 1, 8, 0, 0)

    def test_every_5min(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="*/5 * * * *")
        now = datetime(2025, 3, 1, 12, 3, 0)
        result = compute_next_run_at(s, now)
        assert result == datetime(2025, 3, 1, 12, 5, 0)

    def test_after_8am_goes_to_next_day(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *")
        now = datetime(2025, 3, 1, 9, 0, 0)
        result = compute_next_run_at(s, now)
        assert result == datetime(2025, 3, 2, 8, 0, 0)

    def test_empty_expr(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="")
        assert compute_next_run_at(s, datetime(2025, 1, 1)) is None

    def test_invalid_expr(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="not a cron")
        assert compute_next_run_at(s, datetime(2025, 1, 1)) is None

    def test_none_expr(self):
        s = CronSchedule(kind=CronScheduleKind.CRON)
        assert compute_next_run_at(s, datetime(2025, 1, 1)) is None

    def test_weekly_monday(self):
        s = CronSchedule(kind=CronScheduleKind.CRON, expr="0 9 * * 1")
        # 2025-03-01 是周六
        now = datetime(2025, 3, 1, 10, 0, 0)
        result = compute_next_run_at(s, now)
        # 下一个周一 = 2025-03-03
        assert result == datetime(2025, 3, 3, 9, 0, 0)
