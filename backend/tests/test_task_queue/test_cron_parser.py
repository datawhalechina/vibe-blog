"""
test_cron_parser.py — 自然语言时间解析测试 (P1-P11)
"""
from datetime import datetime

import pytest

from services.task_queue.cron_parser import parse_schedule


class TestRecurring:
    """P1-P7: 周期性任务解析"""

    def test_p1_daily_morning(self):
        """P1: 每天早上8点"""
        r = parse_schedule("每天早上8点")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "0 8 * * *"

    def test_p2_daily_afternoon(self):
        """P2: 每天下午3点"""
        r = parse_schedule("每天下午3点")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "0 15 * * *"

    def test_p3_workday(self):
        """P3: 每个工作日早上9点"""
        r = parse_schedule("每个工作日早上9点")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "0 9 * * 1-5"

    def test_p4_weekly(self):
        """P4: 每周一10点"""
        r = parse_schedule("每周一10点")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "0 10 * * 1"

    def test_p5_every_n_hours(self):
        """P5: 每2小时"""
        r = parse_schedule("每2小时")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "0 */2 * * *"

    def test_p6_every_n_minutes(self):
        """P6: 每30分钟"""
        r = parse_schedule("每30分钟")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "*/30 * * * *"

    def test_p7_monthly(self):
        """P7: 每月1号8点"""
        r = parse_schedule("每月1号8点")
        assert r['type'] == 'cron'
        assert r['cron_expression'] == "0 8 1 * *"


class TestOnce:
    """P8-P10: 一次性任务解析"""

    def test_p8_today(self):
        """P8: 今天下午3点"""
        r = parse_schedule("今天下午3点")
        assert r['type'] == 'once'
        assert '15:00' in r['scheduled_at']

    def test_p9_tomorrow(self):
        """P9: 明天早上8点"""
        r = parse_schedule("明天早上8点")
        assert r['type'] == 'once'
        assert '08:00' in r['scheduled_at']

    def test_p10_day_after(self):
        """P10: 后天下午2点"""
        r = parse_schedule("后天下午2点")
        assert r['type'] == 'once'
        assert '14:00' in r['scheduled_at']


class TestError:
    """P11: 错误处理"""

    def test_p11_unparseable(self):
        """P11: 无法解析的输入"""
        r = parse_schedule("随便什么时候")
        assert r['type'] == 'error'
        assert 'error' in r
