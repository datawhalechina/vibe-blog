"""
Tests for Questioner Loop Bug Fix:
1. StyleProfile.max_questioning_rounds field with correct defaults per mode
2. _should_deepen() uses StyleProfile instead of hardcoded MAX_DEEPEN_ROUNDS
3. questioner.j2 dynamic depth_score thresholds
"""

import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# Test Group 1: StyleProfile.max_questioning_rounds
# ============================================================

class TestStyleProfileMaxQuestioningRounds:
    """StyleProfile should have max_questioning_rounds with correct per-mode values."""

    def test_default_value_is_2(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        profile = StyleProfile()
        assert profile.max_questioning_rounds == 2

    def test_mini_mode_is_1(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        profile = StyleProfile.mini()
        assert profile.max_questioning_rounds == 1

    def test_short_mode_is_1(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        profile = StyleProfile.short()
        assert profile.max_questioning_rounds == 1

    def test_medium_mode_is_2(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        profile = StyleProfile.medium()
        assert profile.max_questioning_rounds == 2

    def test_long_mode_is_3(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        profile = StyleProfile.long()
        assert profile.max_questioning_rounds == 3


# ============================================================
# Test Group 2: _should_deepen uses StyleProfile
# ============================================================

class TestShouldDeepenUsesStyleProfile:
    """_should_deepen should use StyleProfile.max_questioning_rounds, not hardcoded limit."""

    def _make_generator(self, style=None):
        """Create a BlogGenerator with mocked dependencies."""
        from backend.services.blog_generator.style_profile import StyleProfile
        from backend.services.blog_generator.generator import BlogGenerator

        mock_llm = MagicMock()
        gen = BlogGenerator(llm_client=mock_llm, style=style or StyleProfile.mini())
        return gen

    def test_mini_stops_after_1_round(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        gen = self._make_generator(style=StyleProfile.mini())
        state = {
            'questioning_count': 1,
            'all_sections_detailed': False,
            'target_length': 'mini',
        }
        assert gen._should_deepen(state) == "continue"

    def test_mini_allows_first_round(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        gen = self._make_generator(style=StyleProfile.mini())
        state = {
            'questioning_count': 0,
            'all_sections_detailed': False,
            'target_length': 'mini',
        }
        assert gen._should_deepen(state) == "deepen"

    def test_long_allows_up_to_3_rounds(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        gen = self._make_generator(style=StyleProfile.long())
        state = {
            'questioning_count': 2,
            'all_sections_detailed': False,
            'target_length': 'long',
        }
        assert gen._should_deepen(state) == "deepen"

    def test_long_stops_at_3(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        gen = self._make_generator(style=StyleProfile.long())
        state = {
            'questioning_count': 3,
            'all_sections_detailed': False,
            'target_length': 'long',
        }
        assert gen._should_deepen(state) == "continue"

    def test_returns_continue_when_all_detailed(self):
        from backend.services.blog_generator.style_profile import StyleProfile
        gen = self._make_generator(style=StyleProfile.medium())
        state = {
            'questioning_count': 0,
            'all_sections_detailed': True,
            'target_length': 'medium',
        }
        assert gen._should_deepen(state) == "continue"

    def test_no_hardcoded_max_deepen_rounds(self):
        """Verify the old MAX_DEEPEN_ROUNDS=5 constant is removed."""
        import inspect
        from backend.services.blog_generator.generator import BlogGenerator
        source = inspect.getsource(BlogGenerator._should_deepen)
        assert "MAX_DEEPEN_ROUNDS" not in source


# ============================================================
# Test Group 3: questioner.j2 dynamic thresholds
# ============================================================

class TestQuestionerTemplateDynamicThresholds:
    """questioner.j2 should use dynamic depth_score thresholds based on depth_requirement."""

    def _render_template(self, depth_requirement: str) -> str:
        """Render questioner.j2 with given depth_requirement."""
        from backend.services.blog_generator.prompts import get_prompt_manager
        pm = get_prompt_manager()
        return pm.render_questioner(
            section_content="test content",
            section_outline={"title": "test"},
            depth_requirement=depth_requirement,
        )

    def test_minimal_threshold_50(self):
        rendered = self._render_template("minimal")
        assert "depth_score >= 50" in rendered

    def test_shallow_threshold_60(self):
        rendered = self._render_template("shallow")
        assert "depth_score >= 60" in rendered

    def test_medium_threshold_75(self):
        rendered = self._render_template("medium")
        assert "depth_score >= 75" in rendered

    def test_deep_threshold_80(self):
        rendered = self._render_template("deep")
        assert "depth_score >= 80" in rendered
