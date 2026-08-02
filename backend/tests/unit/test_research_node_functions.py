import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.blog_generator.orchestrator.nodes.research import (
    check_knowledge_node,
    enhance_with_knowledge_node,
    planner_node,
    refine_search_node,
    researcher_node,
)


RESEARCH_NODES = (
    researcher_node,
    planner_node,
    check_knowledge_node,
    refine_search_node,
    enhance_with_knowledge_node,
)


def test_research_nodes_use_explicit_keyword_dependencies():
    for node in RESEARCH_NODES:
        parameters = inspect.signature(node).parameters
        assert "generator" not in parameters
        assert "context" not in parameters
        assert list(parameters)[0] == "state"
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in list(parameters.values())[1:]
        )


def test_researcher_skip_populates_writer_safe_defaults_without_dependencies():
    researcher = MagicMock()
    layer_validator = MagicMock()
    state = {
        "skip_researcher": True,
        "background_knowledge": None,
        "search_results": None,
        "distilled_sources": None,
    }

    result = researcher_node(
        state,
        researcher=researcher,
        layer_validator=layer_validator,
    )

    assert result["background_knowledge"] == ""
    assert result["search_results"] == []
    assert result["distilled_sources"] == []
    researcher.run.assert_not_called()
    layer_validator.validate_inputs.assert_not_called()


def test_planner_auto_confirms_mini_and_injects_writing_skill():
    planner = MagicMock()
    planner.run.return_value = {"outline": {"title": "Title", "sections": []}}
    skill = SimpleNamespace(name="tutorial")
    skill_manager = MagicMock()
    skill_manager.match_skill.return_value = skill
    skill_manager.build_system_prompt_section.return_value = "Use tutorial structure"
    interrupt = MagicMock()

    result = planner_node(
        {"topic": "Topic", "article_type": "tutorial", "target_length": "mini"},
        planner=planner,
        layer_validator=None,
        on_stream=None,
        interactive=True,
        writing_skill_manager=skill_manager,
        llm_client=MagicMock(),
        interrupt_fn=interrupt,
        getenv=lambda key, default=None: default,
        image_preplanner_factory=MagicMock(),
    )

    assert result["_writing_skill_prompt"] == "Use tutorial structure"
    interrupt.assert_not_called()


def test_enhance_with_knowledge_updates_successful_sections_in_order():
    writer = SimpleNamespace(llm=MagicMock())
    executor = MagicMock()
    executor.run_parallel.return_value = [
        SimpleNamespace(success=True, result="Enhanced one", error=None),
        SimpleNamespace(success=False, result=None, error="failed"),
    ]
    prompt_manager = MagicMock()
    prompt_manager.render_writer_enhance_with_knowledge.return_value = "prompt"
    state = {
        "sections": [
            {"id": "one", "title": "One", "content": "Old one"},
            {"id": "two", "title": "Two", "content": "Old two"},
        ],
        "knowledge_gaps": [
            {"section_id": "one"},
            {"section_id": "two"},
        ],
        "accumulated_knowledge": "Knowledge",
    }

    result = enhance_with_knowledge_node(
        state,
        writer=writer,
        parallel_executor=executor,
        prompt_manager_factory=MagicMock(return_value=prompt_manager),
        task_config_factory=MagicMock(return_value="config"),
    )

    assert result["sections"][0]["content"] == "Enhanced one"
    assert result["sections"][1]["content"] == "Old two"
    assert result["knowledge_gaps"] == []
