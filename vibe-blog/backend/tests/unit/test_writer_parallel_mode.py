"""
Tests for writer mini mode forced parallel execution.

When target_length is 'mini', _should_use_parallel() must return True
regardless of TRACE_ENABLED setting.
"""

import os
import pytest
from unittest.mock import patch

from services.blog_generator.agents.writer import _should_use_parallel


class TestShouldUseParallelWithMode:
    """_should_use_parallel accepts a mode parameter for mini forced parallel."""

    def test_mini_mode_forces_parallel_even_when_trace_enabled(self):
        """mini mode must return True even if TRACE_ENABLED=true."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert _should_use_parallel(mode='mini') is True

    def test_mini_mode_forces_parallel_when_trace_disabled(self):
        """mini mode returns True when trace is disabled (normal case)."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'false'}):
            assert _should_use_parallel(mode='mini') is True

    def test_non_mini_mode_respects_trace_enabled(self):
        """Non-mini modes should still disable parallel when trace is on."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert _should_use_parallel(mode='medium') is False

    def test_non_mini_mode_allows_parallel_when_trace_disabled(self):
        """Non-mini modes allow parallel when trace is off."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'false'}):
            assert _should_use_parallel(mode='medium') is True

    def test_no_mode_defaults_to_original_behavior_trace_on(self):
        """No mode argument preserves original behavior: trace on -> no parallel."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert _should_use_parallel() is False

    def test_no_mode_defaults_to_original_behavior_trace_off(self):
        """No mode argument preserves original behavior: trace off -> parallel."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'false'}):
            assert _should_use_parallel() is True

    def test_none_mode_same_as_no_mode(self):
        """Explicitly passing mode=None behaves like no mode."""
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert _should_use_parallel(mode=None) is False
