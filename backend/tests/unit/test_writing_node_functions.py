import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.blog_generator.orchestrator.nodes.writing import (
    deepen_content_node,
    questioner_node,
    section_evaluate_node,
    section_improve_node,
    writer_node,
)


WRITING_NODES = (
    writer_node,
    questioner_node,
    deepen_content_node,
    section_evaluate_node,
    section_improve_node,
)


def test_writing_nodes_use_explicit_keyword_dependencies():
    for node in WRITING_NODES:
        parameters = inspect.signature(node).parameters
        assert "generator" not in parameters
        assert "context" not in parameters
        assert list(parameters)[0] == "state"
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in list(parameters.values())[1:]
        )


def test_writer_injects_memory_and_persona_then_initializes_accumulated_knowledge():
    writer = MagicMock()
    writer.run.side_effect = lambda state: state
    memory_storage = MagicMock()
    memory_storage.format_for_injection.return_value = "Remember concise examples"
    style = MagicMock()
    style.get_persona_prompt.return_value = "Write as an engineer"
    state = {
        "user_id": "user-1",
        "background_knowledge": "Background",
        "sections": [],
    }

    result = writer_node(
        state,
        writer=writer,
        layer_validator=None,
        memory_storage=memory_storage,
        configured_style=style,
    )

    assert result["background_knowledge"] == (
        "Background\n\nRemember concise examples"
    )
    assert result["_persona_prompt"] == "Write as an engineer"
    assert result["accumulated_knowledge"] == result["background_knowledge"]


def test_deepen_content_updates_only_successful_section_and_tracks_snapshot():
    writer = MagicMock()
    executor = MagicMock()
    executor.run_parallel.return_value = [
        SimpleNamespace(success=True, result="Deepened", error=None)
    ]
    tracker = MagicMock()
    state = {
        "sections": [
            {"id": "one", "title": "One", "content": "Old"},
            {"id": "two", "title": "Two", "content": "Keep"},
        ],
        "question_results": [
            {
                "section_id": "one",
                "is_detailed_enough": False,
                "vague_points": ["details"],
            }
        ],
    }

    result = deepen_content_node(
        state,
        writer=writer,
        parallel_executor=executor,
        tracker=tracker,
        task_config_factory=MagicMock(return_value="config"),
    )

    assert result["sections"][0]["content"] == "Deepened"
    assert result["sections"][1]["content"] == "Keep"
    assert result["questioning_count"] == 1
    tracker.log_deepen_snapshot.assert_called_once()


def test_section_evaluate_disabled_preserves_skip_contract():
    state = {"sections": [{"title": "One", "content": "Body"}]}
    result = section_evaluate_node(
        state,
        questioner=MagicMock(),
        tracker=MagicMock(),
        configured_style=SimpleNamespace(enable_thread_check=False),
    )

    assert result["section_evaluations"] == []
    assert result["needs_section_improvement"] is False


def test_section_improve_updates_low_scoring_sections_and_tracker():
    writer = MagicMock()
    writer.improve_section.return_value = "Improved"
    tracker = MagicMock()
    state = {
        "sections": [{"title": "One", "content": "Old"}],
        "section_evaluations": [{"section_idx": 0, "overall_quality": 6.5}],
        "prev_section_avg_score": 6.5,
    }

    result = section_improve_node(state, writer=writer, tracker=tracker)

    assert result["sections"][0]["content"] == "Improved"
    assert result["section_improve_count"] == 1
    tracker.log_section_improve_snapshot.assert_called_once()
