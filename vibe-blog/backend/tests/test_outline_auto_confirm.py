"""
Tests for outline auto-confirm feature.

When target_length is 'mini' or OUTLINE_AUTO_CONFIRM env var is 'true',
the planner node should skip the interactive interrupt and auto-confirm the outline.
"""

import os
import logging
import types
from unittest.mock import MagicMock, patch

import pytest

# Import the real _planner_node method to bind to our mock object
from services.blog_generator.generator import BlogGenerator


def _make_planner_result():
    """Standard planner result with a valid outline."""
    return {
        'outline': {
            'title': 'Test Outline',
            'sections': [
                {'title': 'Section 1', 'narrative_role': 'intro', 'narrative_mode': ''},
                {'title': 'Section 2', 'narrative_role': 'body', 'narrative_mode': ''},
            ],
            'narrative_mode': 'linear',
            'narrative_flow': {},
        },
        'sections': [],
    }


@pytest.fixture
def mock_generator():
    """Create a lightweight mock with the real _planner_node bound to it."""
    gen = MagicMock()
    # Bind the real _planner_node method
    gen._planner_node = types.MethodType(BlogGenerator._planner_node, gen)
    # Configure attributes used by _planner_node
    gen._interactive = True
    gen._outline_stream_callback = None
    gen._writing_skill_manager = None
    gen.planner.run = MagicMock(return_value=_make_planner_result())
    return gen


class TestOutlineAutoConfirmMini:
    """Tests: mini mode should auto-confirm outline without calling interrupt."""

    @patch('services.blog_generator.generator.interrupt')
    def test_mini_mode_skips_interrupt(self, mock_interrupt, mock_generator):
        """When target_length='mini', interrupt() should NOT be called."""
        state = {'target_length': 'mini', 'topic': 'test'}
        result = mock_generator._planner_node(state)

        mock_interrupt.assert_not_called()
        assert result.get('outline') is not None

    @patch('services.blog_generator.generator.interrupt')
    def test_mini_mode_logs_auto_confirm(self, mock_interrupt, mock_generator, caplog):
        """When auto-confirming, should log an AutoConfirm message."""
        state = {'target_length': 'mini', 'topic': 'test'}
        with caplog.at_level(logging.INFO):
            mock_generator._planner_node(state)

        assert any('[AutoConfirm]' in record.message for record in caplog.records)


class TestOutlineAutoConfirmEnvVar:
    """Tests: OUTLINE_AUTO_CONFIRM=true should auto-confirm outline."""

    @patch('services.blog_generator.generator.interrupt')
    def test_env_var_true_skips_interrupt(self, mock_interrupt, mock_generator):
        """When OUTLINE_AUTO_CONFIRM=true, interrupt() should NOT be called."""
        state = {'target_length': 'medium', 'topic': 'test'}
        with patch.dict(os.environ, {'OUTLINE_AUTO_CONFIRM': 'true'}):
            result = mock_generator._planner_node(state)

        mock_interrupt.assert_not_called()
        assert result.get('outline') is not None

    @patch('services.blog_generator.generator.interrupt')
    def test_env_var_True_case_insensitive(self, mock_interrupt, mock_generator):
        """OUTLINE_AUTO_CONFIRM should be case-insensitive."""
        state = {'target_length': 'medium', 'topic': 'test'}
        with patch.dict(os.environ, {'OUTLINE_AUTO_CONFIRM': 'True'}):
            mock_generator._planner_node(state)

        mock_interrupt.assert_not_called()

    @patch('services.blog_generator.generator.interrupt')
    def test_env_var_false_does_not_skip(self, mock_interrupt, mock_generator):
        """When OUTLINE_AUTO_CONFIRM=false and target_length=medium, interrupt IS called."""
        mock_interrupt.return_value = {"action": "confirm"}
        state = {'target_length': 'medium', 'topic': 'test'}
        with patch.dict(os.environ, {'OUTLINE_AUTO_CONFIRM': 'false'}):
            mock_generator._planner_node(state)

        mock_interrupt.assert_called_once()


class TestOutlineNormalInterrupt:
    """Tests: medium/long mode without env override should call interrupt normally."""

    @patch('services.blog_generator.generator.interrupt')
    def test_medium_mode_calls_interrupt(self, mock_interrupt, mock_generator):
        """When target_length='medium' and no env override, interrupt() IS called."""
        mock_interrupt.return_value = {"action": "confirm"}
        state = {'target_length': 'medium', 'topic': 'test'}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OUTLINE_AUTO_CONFIRM', None)
            mock_generator._planner_node(state)

        mock_interrupt.assert_called_once()

    @patch('services.blog_generator.generator.interrupt')
    def test_long_mode_calls_interrupt(self, mock_interrupt, mock_generator):
        """When target_length='long', interrupt() IS called."""
        mock_interrupt.return_value = {"action": "confirm"}
        state = {'target_length': 'long', 'topic': 'test'}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OUTLINE_AUTO_CONFIRM', None)
            mock_generator._planner_node(state)

        mock_interrupt.assert_called_once()

    @patch('services.blog_generator.generator.interrupt')
    def test_interrupt_edit_action_still_works(self, mock_interrupt, mock_generator):
        """When user edits the outline via interrupt, the edit should be applied."""
        edited_outline = {
            'title': 'Edited Title',
            'sections': [{'title': 'New Section'}],
        }
        mock_interrupt.return_value = {"action": "edit", "outline": edited_outline}
        state = {'target_length': 'medium', 'topic': 'test'}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OUTLINE_AUTO_CONFIRM', None)
            result = mock_generator._planner_node(state)

        assert result['outline']['title'] == 'Edited Title'
        assert result['sections'] == []


class TestOutlineAutoConfirmNonInteractive:
    """Tests: non-interactive mode should never call interrupt regardless."""

    @patch('services.blog_generator.generator.interrupt')
    def test_non_interactive_skips_interrupt(self, mock_interrupt, mock_generator):
        """When _interactive=False, interrupt should not be called even for medium."""
        mock_generator._interactive = False
        state = {'target_length': 'medium', 'topic': 'test'}
        mock_generator._planner_node(state)

        mock_interrupt.assert_not_called()
