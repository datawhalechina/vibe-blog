"""
T1: 指数退避计算测试
"""
import pytest
from services.task_queue.backoff import error_backoff_seconds


class TestErrorBackoff:
    def test_zero_errors(self):
        assert error_backoff_seconds(0) == 0

    def test_negative_errors(self):
        assert error_backoff_seconds(-1) == 0

    def test_first_error(self):
        assert error_backoff_seconds(1) == 30

    def test_second_error(self):
        assert error_backoff_seconds(2) == 60

    def test_third_error(self):
        assert error_backoff_seconds(3) == 300

    def test_fourth_error(self):
        assert error_backoff_seconds(4) == 900

    def test_fifth_error(self):
        assert error_backoff_seconds(5) == 3600

    def test_clamp_at_max(self):
        assert error_backoff_seconds(100) == 3600

    def test_monotonically_increasing(self):
        values = [error_backoff_seconds(i) for i in range(1, 10)]
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1]
