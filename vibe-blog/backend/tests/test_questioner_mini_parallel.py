"""
Tests for _should_use_parallel mini mode forced parallel.

mini mode should always return True for parallel, regardless of TRACE_ENABLED.
Other modes should respect TRACE_ENABLED as before.
"""

import os
import pytest
from unittest.mock import patch


class TestShouldUseParallelMiniMode:
    """_should_use_parallel(mode='mini') should always return True."""

    def _get_fn(self):
        from backend.services.blog_generator.agents.questioner import _should_use_parallel
        return _should_use_parallel

    def test_mini_mode_returns_true_without_trace(self):
        fn = self._get_fn()
        with patch.dict(os.environ, {'TRACE_ENABLED': 'false'}):
            assert fn(mode='mini') is True

    def test_mini_mode_returns_true_even_with_trace_enabled(self):
        """Key behavior: mini forces parallel even when tracing is on."""
        fn = self._get_fn()
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert fn(mode='mini') is True

    def test_non_mini_mode_disabled_by_trace(self):
        fn = self._get_fn()
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert fn(mode='medium') is False

    def test_non_mini_mode_enabled_without_trace(self):
        fn = self._get_fn()
        with patch.dict(os.environ, {'TRACE_ENABLED': 'false'}):
            assert fn(mode='medium') is True

    def test_none_mode_respects_trace(self):
        """Default (no mode) should behave like before."""
        fn = self._get_fn()
        with patch.dict(os.environ, {'TRACE_ENABLED': 'true'}):
            assert fn() is False

    def test_none_mode_parallel_without_trace(self):
        fn = self._get_fn()
        with patch.dict(os.environ, {'TRACE_ENABLED': 'false'}):
            assert fn() is True
