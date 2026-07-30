import json

import pytest
from pydantic import ValidationError

from services.blog_generator.schemas.outputs import (
    ArtistGenerationOutput,
    CodeGenerationOutput,
    CredibilityScoresOutput,
    DepthCheckOutput,
    DetectedKnowledgeGapsOutput,
    FactCheckOutput,
    GoalExtractionOutput,
    HumanizerRewriteOutput,
    PlannerOutlineOutput,
    QueryListOutput,
    ResearchSummaryOutput,
    ReviewerOutput,
    SearchRouterOutput,
    SourceDistillationOutput,
    SummaryOutput,
)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            ArtistGenerationOutput,
            {"render_method": "mermaid", "content": "flowchart TD", "caption": "Flow"},
        ),
        (
            CodeGenerationOutput,
            {"code_block": "print(1)", "output_block": "1", "explanation": "Demo"},
        ),
        (
            FactCheckOutput,
            {"score": 5, "claims": [], "fixes": []},
        ),
        (
            GoalExtractionOutput,
            {"rational": "why", "evidence": "source", "summary": "result"},
        ),
        (
            HumanizerRewriteOutput,
            {"replacements": [{"old": "before", "new": "after"}]},
        ),
        (
            SummaryOutput,
            {
                "tldr": "Short",
                "seo_keywords": ["one"],
                "social_summary": "Social",
                "meta_description": "Meta",
            },
        ),
        (
            SearchRouterOutput,
            {"sources": ["github"], "arxiv_query": "", "blog_query": "topic"},
        ),
    ],
)
def test_consumer_models_accept_representative_payloads(model, payload):
    dumped = model.model_validate(payload).model_dump(mode="json")
    assert all(dumped[key] == value for key, value in payload.items())


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (ArtistGenerationOutput, {"render_method": "mermaid", "content": "x"}),
        (CodeGenerationOutput, {"code_block": [], "output_block": "", "explanation": ""}),
        (GoalExtractionOutput, {"rational": "why", "evidence": "source"}),
        (SummaryOutput, {"tldr": "Short", "seo_keywords": "one"}),
    ],
)
def test_consumer_models_reject_missing_or_wrong_fields(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_query_list_accepts_array_and_legacy_wrapper():
    assert QueryListOutput.model_validate(["one", "two"]).root == ["one", "two"]
    assert QueryListOutput.model_validate({"queries": ["one", "two"]}).root == [
        "one",
        "two",
    ]


def test_credibility_scores_accept_legacy_wrapper():
    result = CredibilityScoresOutput.model_validate(
        {
            "results": [
                {
                    "index": 1,
                    "authority": 8,
                    "freshness": 9,
                    "relevance": 10,
                    "depth": 7,
                    "total_score": 8.6,
                    "reason": "Official source",
                }
            ]
        }
    )

    assert result.root[0].index == 1


def test_planner_schema_requires_title_and_sections_but_preserves_extensions():
    result = PlannerOutlineOutput.model_validate(
        {
            "title": "Guide",
            "sections": [{"title": "Intro", "custom_field": "kept"}],
            "narrative_mode": "tutorial",
        }
    )

    dumped = result.model_dump(mode="json")
    assert dumped["sections"][0]["custom_field"] == "kept"
    assert dumped["narrative_mode"] == "tutorial"

    with pytest.raises(ValidationError):
        PlannerOutlineOutput.model_validate({"title": "Guide"})


def test_reviewer_schema_rejects_invalid_nested_severity():
    with pytest.raises(ValidationError):
        ReviewerOutput.model_validate(
            {
                "score": 70,
                "issues": [
                    {
                        "section_id": "one",
                        "issue_type": "logic",
                        "severity": "urgent",
                        "description": "Problem",
                        "suggestion": "Fix it",
                    }
                ],
                "summary": "Needs work",
            }
        )


def test_research_summary_validates_nested_instructional_analysis():
    result = ResearchSummaryOutput.model_validate(
        {
            "background_knowledge": "Background",
            "key_concepts": [{"name": "Agent", "description": "Worker"}],
            "top_references": [{"title": "Docs", "url": "https://example.com"}],
            "instructional_analysis": {
                "learning_objectives": [
                    {"type": "primary", "objective": "Understand agents"}
                ],
                "audience": {
                    "knowledge_level": "beginner",
                    "reading_purpose": "learn",
                    "expected_outcome": "understand",
                },
                "content_type": "tutorial",
                "verbatim_data": [],
            },
        }
    )

    dumped = result.model_dump(mode="json")
    json.dumps(dumped)
    assert dumped["instructional_analysis"]["content_type"] == "tutorial"


def test_root_models_validate_nested_item_types():
    gaps = DetectedKnowledgeGapsOutput.model_validate(
        [{"gap": "Missing details", "refined_query": "details"}]
    )
    assert gaps.root[0].refined_query == "details"

    depth = DepthCheckOutput.model_validate(
        {
            "is_detailed_enough": False,
            "depth_score": 60,
            "vague_points": [
                {"location": "claim", "question": "Evidence?", "suggestion": "data"}
            ],
        }
    )
    assert depth.vague_points[0].question == "Evidence?"


def test_source_distillation_dump_is_json_compatible():
    result = SourceDistillationOutput.model_validate(
        {
            "sources": [],
            "common_themes": [],
            "contradictions": [],
            "material_by_type": {
                "concepts": [],
                "cases": [],
                "data": [],
                "comparisons": [],
            },
        }
    )

    json.dumps(result.model_dump(mode="json"))
