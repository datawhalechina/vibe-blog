import json

import pytest

from services.blog_generator.schemas.state_contracts import (
    STABLE_STATE_FIELDS,
    StateContractError,
    validate_state_fields,
)


VALID_PAYLOADS = {
    "outline": {
        "title": "Guide",
        "sections": [{"title": "Intro", "custom_section": "kept"}],
        "narrative_mode": "tutorial",
    },
    "sections": [
        {
            "id": "section_1",
            "title": "Intro",
            "content": "Body",
            "custom_section": "kept",
        }
    ],
    "code_blocks": [
        {
            "id": "code_1",
            "code": "print(1)",
            "output": "1",
            "explanation": "Demo",
            "language": "python",
            "custom_code": "kept",
        }
    ],
    "images": [
        {
            "id": "image_1",
            "render_method": "enhanced_mermaid",
            "content": "flowchart TD",
            "caption": "Flow",
            "custom_image": "kept",
        }
    ],
    "question_results": [
        {
            "section_id": "section_1",
            "is_detailed_enough": False,
            "depth_score": 60,
            "vague_points": [
                {
                    "location": "claim",
                    "question": "Evidence?",
                    "suggestion": "data",
                    "custom_question": "kept",
                }
            ],
        }
    ],
    "review_issues": [
        {
            "section_id": "section_1",
            "issue_type": "logic",
            "severity": "high",
            "description": "Problem",
            "suggestion": "Fix",
            "custom_review": "kept",
        },
        {
            "section_id": "section_1",
            "check_type": "transition",
            "severity": "medium",
            "description": "Abrupt",
            "suggestion": "Bridge",
        },
    ],
    "instructional_analysis": {
        "learning_objectives": [
            {"type": "primary", "objective": "Understand contracts"}
        ],
        "content_type": "tutorial",
        "verbatim_data": [],
        "custom_analysis": "kept",
    },
    "knowledge_gaps": [
        {
            "gap_type": "missing_data",
            "description": "Missing benchmark",
            "suggested_query": "benchmark",
            "section_id": "section_1",
            "custom_gap": "kept",
        }
    ],
}


INVALID_PAYLOADS = {
    "outline": {"sections": []},
    "sections": [{"id": 1, "title": "Intro", "content": "Body"}],
    "code_blocks": [
        {
            "id": "code_1",
            "code": [],
            "output": "",
            "explanation": "Demo",
        }
    ],
    "images": [
        {
            "id": "image_1",
            "render_method": "svg",
            "content": "x",
            "caption": "Image",
        }
    ],
    "question_results": [
        {
            "section_id": "section_1",
            "is_detailed_enough": False,
            "depth_score": 101,
            "vague_points": [],
        }
    ],
    "review_issues": [
        {
            "section_id": "section_1",
            "issue_type": "logic",
            "severity": "urgent",
            "description": "Problem",
            "suggestion": "Fix",
        }
    ],
    "instructional_analysis": {"content_type": "unknown"},
    "knowledge_gaps": [
        {
            "gap_type": "unknown",
            "description": "Gap",
            "suggested_query": "query",
        }
    ],
}


def test_stable_field_registry_covers_exact_pr3_scope():
    assert STABLE_STATE_FIELDS == frozenset(VALID_PAYLOADS)


@pytest.mark.parametrize("field", VALID_PAYLOADS)
def test_validate_state_fields_preserves_json_payloads_and_extensions(field):
    state = {field: VALID_PAYLOADS[field]}

    result = validate_state_fields(
        state,
        [field],
        node="unit",
        direction="egress",
    )

    assert result is not state
    json.dumps(result[field])
    assert "kept" in json.dumps(result[field])


@pytest.mark.parametrize("field", INVALID_PAYLOADS)
def test_validate_state_fields_identifies_invalid_nested_payload(field):
    with pytest.raises(StateContractError) as raised:
        validate_state_fields(
            {field: INVALID_PAYLOADS[field]},
            [field],
            node="writer",
            direction="egress",
        )

    assert raised.value.field == field
    assert raised.value.node == "writer"
    assert raised.value.direction == "egress"
    assert raised.value.details


def test_validate_state_fields_skips_absent_optional_field():
    state = {"topic": "Contracts"}

    result = validate_state_fields(
        state,
        ["outline"],
        node="planner",
        direction="ingress",
    )

    assert result == state
    assert result is not state


def test_validate_state_fields_does_not_inject_model_defaults():
    section = {
        "id": "section_1",
        "title": "Intro",
        "content": "Body",
    }

    result = validate_state_fields(
        {"sections": [section]},
        ["sections"],
        node="writer",
        direction="egress",
    )

    assert result["sections"] == [section]


def test_instructional_analysis_preserves_nested_extensions():
    analysis = {
        "learning_objectives": [
            {
                "type": "primary",
                "objective": "Understand contracts",
                "objective_extension": "kept",
            }
        ],
        "audience": {
            "knowledge_level": "intermediate",
            "reading_purpose": "Build safely",
            "expected_outcome": "Stable checkpoints",
            "audience_extension": "kept",
        },
        "content_type": "tutorial",
        "verbatim_data": [
            {
                "type": "term",
                "value": "SharedState",
                "verbatim_extension": "kept",
            }
        ],
    }

    result = validate_state_fields(
        {"instructional_analysis": analysis},
        ["instructional_analysis"],
        node="researcher",
        direction="egress",
    )["instructional_analysis"]

    assert result["learning_objectives"][0]["objective_extension"] == "kept"
    assert result["audience"]["audience_extension"] == "kept"
    assert result["verbatim_data"][0]["verbatim_extension"] == "kept"


def test_validate_state_fields_rejects_unknown_contract_name():
    with pytest.raises(ValueError, match="Unknown stable state field"):
        validate_state_fields(
            {},
            ["unknown"],
            node="unit",
            direction="ingress",
        )
