"""
Test: StyleProfile.mini() preset should match mini.yaml configuration.

The mini preset is the lightest pipeline — fact_check, humanizer, and
summary_gen must all be disabled to avoid unnecessary processing time.
"""

import pytest
from services.blog_generator.style_profile import StyleProfile


class TestMiniPresetFlags:
    """Verify mini() agent flags align with mini.yaml."""

    def test_fact_check_disabled(self):
        profile = StyleProfile.mini()
        assert profile.enable_fact_check is False, (
            "mini preset should disable fact_check (mini.yaml: false)"
        )

    def test_humanizer_disabled(self):
        profile = StyleProfile.mini()
        assert profile.enable_humanizer is False, (
            "mini preset should disable humanizer (mini.yaml: false)"
        )

    def test_summary_gen_disabled(self):
        profile = StyleProfile.mini()
        assert profile.enable_summary_gen is False, (
            "mini preset should disable summary_gen (mini.yaml: false)"
        )

    def test_unchanged_flags_still_correct(self):
        """Flags that should remain unchanged after the fix."""
        profile = StyleProfile.mini()
        assert profile.enable_thread_check is False
        assert profile.enable_voice_check is False
        assert profile.enable_text_cleanup is True
        assert profile.enable_ai_boost is False
