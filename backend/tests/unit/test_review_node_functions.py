import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.blog_generator.orchestrator.nodes.review import (
    consistency_check_node,
    cross_section_dedup_node,
    reviewer_node,
    revision_correct_only,
    revision_enhance,
    revision_node,
)


REVIEW_FUNCTIONS = (
    cross_section_dedup_node,
    consistency_check_node,
    reviewer_node,
    revision_node,
    revision_correct_only,
    revision_enhance,
)


def test_review_functions_do_not_accept_generator_or_context():
    for function in REVIEW_FUNCTIONS:
        parameters = inspect.signature(function).parameters
        assert "generator" not in parameters
        assert "context" not in parameters


def test_reviewer_skips_second_review_at_revision_limit():
    reviewer = MagicMock()
    tracker = MagicMock()
    style = SimpleNamespace(max_revision_rounds=1)
    state = {"revision_count": 1}

    result = reviewer_node(
        state,
        reviewer=reviewer,
        tracker=tracker,
        configured_style=style,
    )

    assert result["review_approved"] is True
    reviewer.run.assert_not_called()
    tracker.log_review_score.assert_not_called()


def test_reviewer_merges_consistency_issues_and_tracks_score():
    reviewer = MagicMock()
    reviewer.run.side_effect = lambda state: state
    tracker = MagicMock()
    state = {
        "revision_count": 0,
        "review_score": 8,
        "review_issues": [{"description": "review"}],
        "thread_issues": [{"description": "thread"}],
        "voice_issues": [{"description": "voice"}],
    }

    result = reviewer_node(
        state,
        reviewer=reviewer,
        tracker=tracker,
        configured_style=SimpleNamespace(max_revision_rounds=2),
    )

    assert [issue["description"] for issue in result["review_issues"]] == [
        "review",
        "thread",
        "voice",
    ]
    tracker.log_review_score.assert_called_once()


def test_revision_correct_only_preserves_section_order():
    writer = MagicMock()
    executor = MagicMock()
    executor.run_parallel.return_value = [
        SimpleNamespace(success=True, result="Corrected", error=None)
    ]
    state = {
        "sections": [
            {"id": "one", "title": "One", "content": "Old"},
            {"id": "two", "title": "Two", "content": "Keep"},
        ]
    }

    revision_correct_only(
        state,
        [{"section_id": "one", "description": "Fix"}],
        writer=writer,
        parallel_executor=executor,
        task_config_factory=MagicMock(return_value="config"),
    )

    assert state["sections"][0]["content"] == "Corrected"
    assert state["sections"][1]["content"] == "Keep"


def test_consistency_check_clears_disabled_results():
    state = {
        "sections": [{"id": "one"}, {"id": "two"}],
        "thread_issues": [{"description": "old"}],
        "voice_issues": [{"description": "old"}],
    }
    result = consistency_check_node(
        state,
        configured_style=SimpleNamespace(
            enable_thread_check=False,
            enable_voice_check=False,
        ),
        env_thread_check=True,
        env_voice_check=True,
        thread_checker=MagicMock(),
        voice_checker=MagicMock(),
        parallel_executor=MagicMock(),
        task_config_factory=MagicMock(),
    )

    assert result["thread_issues"] == []
    assert result["voice_issues"] == []
