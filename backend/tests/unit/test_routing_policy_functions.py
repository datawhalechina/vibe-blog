import importlib
import inspect

import pytest

from services.blog_generator.style_profile import StyleProfile


ROUTING_FUNCTIONS = {
    "_should_check_knowledge",
    "_should_refine_search",
    "_should_deepen",
    "_should_continue_questioning",
    "_should_improve_sections",
    "_should_revise",
}


def _routing():
    return importlib.import_module(
        "services.blog_generator.orchestrator.routing"
    )


def test_routing_policy_exposes_module_level_functions_with_explicit_dependencies():
    routing = _routing()

    assert {
        name for name, value in vars(routing).items()
        if name in ROUTING_FUNCTIONS and inspect.isfunction(value)
    } == ROUTING_FUNCTIONS
    assert list(inspect.signature(
        routing._should_check_knowledge
    ).parameters) == ["state"]
    assert list(inspect.signature(
        routing._should_improve_sections
    ).parameters) == ["state"]
    for name in ROUTING_FUNCTIONS - {
        "_should_check_knowledge",
        "_should_improve_sections",
    }:
        assert "style_resolver" in inspect.signature(
            getattr(routing, name)
        ).parameters


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ({"target_length": "mini"}, "skip"),
        ({"target_length": "medium"}, "check"),
        ({}, "check"),
    ],
)
def test_should_check_knowledge_preserves_length_routing(state, expected):
    assert _routing()._should_check_knowledge(state) == expected


def test_should_refine_search_uses_style_and_only_important_gaps():
    routing = _routing()
    state = {
        "target_length": "long",
        "knowledge_gaps": [{"gap_type": "missing_data"}],
        "search_count": 0,
        "max_search_count": 2,
    }

    assert routing._should_refine_search(
        state, style_resolver=routing.RoutingStyleResolver()
    ) == "search"
    assert routing._should_refine_search(
        state, style_resolver=routing.RoutingStyleResolver(StyleProfile.mini())
    ) == "continue"
    state["knowledge_gaps"] = [{"gap_type": "nice_to_have"}]
    assert routing._should_refine_search(
        state, style_resolver=routing.RoutingStyleResolver(StyleProfile.long())
    ) == "continue"


@pytest.mark.parametrize(
    ("state", "style", "expected"),
    [
        (
            {"questioning_count": 0, "all_sections_detailed": False},
            StyleProfile.mini(),
            "deepen",
        ),
        (
            {"questioning_count": 1, "all_sections_detailed": False},
            StyleProfile.mini(),
            "continue",
        ),
        (
            {"questioning_count": 0, "all_sections_detailed": True},
            StyleProfile.long(),
            "continue",
        ),
    ],
)
def test_should_deepen_preserves_round_and_detail_rules(state, style, expected):
    assert _routing()._should_deepen(
        state, style_resolver=_routing().RoutingStyleResolver(style)
    ) == expected


def test_should_continue_questioning_stops_at_style_limit():
    routing = _routing()

    assert routing._should_continue_questioning(
        {"questioning_count": 0},
        style_resolver=routing.RoutingStyleResolver(StyleProfile.mini()),
    ) == "questioner"
    assert routing._should_continue_questioning(
        {"questioning_count": 1},
        style_resolver=routing.RoutingStyleResolver(StyleProfile.mini()),
    ) == "section_evaluate"


def test_should_improve_sections_preserves_convergence_state_update():
    routing = _routing()
    improving = {
        "needs_section_improvement": True,
        "section_improve_count": 0,
        "prev_section_avg_score": 0,
        "section_evaluations": [
            {"overall_quality": 5.0},
            {"overall_quality": 6.0},
        ],
    }

    assert routing._should_improve_sections(improving) == "improve"
    assert improving["prev_section_avg_score"] == 5.5

    converged = {
        "needs_section_improvement": True,
        "section_improve_count": 1,
        "prev_section_avg_score": 6.5,
        "section_evaluations": [
            {"overall_quality": 6.6},
            {"overall_quality": 6.7},
        ],
    }
    assert routing._should_improve_sections(converged) == "continue"
    assert converged["prev_section_avg_score"] == 6.5


def test_should_revise_preserves_limits_filtering_and_full_review():
    routing = _routing()
    high_only = {
        "revision_count": 0,
        "review_issues": [
            {"severity": "high", "description": "critical"},
            {"severity": "medium", "description": "minor"},
        ],
    }

    assert routing._should_revise(
        high_only,
        style_resolver=routing.RoutingStyleResolver(StyleProfile.mini()),
    ) == "revision"
    assert high_only["review_issues"] == [
        {"severity": "high", "description": "critical"}
    ]
    assert routing._should_revise(
        {"revision_count": 1, "review_issues": []},
        style_resolver=routing.RoutingStyleResolver(StyleProfile.mini()),
    ) == "assemble"
    assert routing._should_revise(
        {"revision_count": 0, "review_approved": False},
        style_resolver=routing.RoutingStyleResolver(StyleProfile.medium()),
    ) == "revision"
