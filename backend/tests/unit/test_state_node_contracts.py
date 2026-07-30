import json

import pytest

from services.blog_generator.schemas.state_contracts import (
    NODE_STATE_CONTRACTS,
    StateContractError,
    wrap_node_state_contract,
)


VALID_OUTLINE = {
    "title": "Guide",
    "sections": [{"id": "intro", "title": "Intro"}],
}


def test_writer_contract_declares_stable_reads_and_writes():
    contract = NODE_STATE_CONTRACTS["writer"]

    assert contract.reads == frozenset({"outline"})
    assert contract.writes == frozenset({"sections"})


def test_node_contract_registry_matches_production_state_dependencies():
    actual = {
        name: (contract.reads, contract.writes)
        for name, contract in NODE_STATE_CONTRACTS.items()
    }

    assert actual == {
        "researcher": (frozenset(), frozenset({"instructional_analysis"})),
        "planner": (
            frozenset({"instructional_analysis"}),
            frozenset({"outline", "sections"}),
        ),
        "writer": (frozenset({"outline"}), frozenset({"sections"})),
        "check_knowledge": (
            frozenset({"outline", "sections"}),
            frozenset({"knowledge_gaps"}),
        ),
        "refine_search": (frozenset({"knowledge_gaps"}), frozenset()),
        "enhance_with_knowledge": (
            frozenset({"knowledge_gaps", "sections"}),
            frozenset({"knowledge_gaps", "sections"}),
        ),
        "questioner": (
            frozenset({"outline", "sections"}),
            frozenset({"question_results"}),
        ),
        "deepen_content": (
            frozenset({"question_results", "sections"}),
            frozenset({"sections"}),
        ),
        "section_evaluate": (frozenset({"sections"}), frozenset()),
        "section_improve": (
            frozenset({"sections"}),
            frozenset({"sections"}),
        ),
        "coder_and_artist": (
            frozenset({"sections"}),
            frozenset({"code_blocks", "sections"}),
        ),
        "cross_section_dedup": (
            frozenset({"sections"}),
            frozenset({"sections"}),
        ),
        "consistency_check": (
            frozenset({"outline", "sections"}),
            frozenset(),
        ),
        "reviewer": (
            frozenset({"outline", "sections"}),
            frozenset({"review_issues"}),
        ),
        "revision": (
            frozenset({"review_issues", "sections"}),
            frozenset({"sections"}),
        ),
        "factcheck": (frozenset({"sections"}), frozenset({"sections"})),
        "text_cleanup": (frozenset({"sections"}), frozenset({"sections"})),
        "humanizer": (frozenset({"sections"}), frozenset({"sections"})),
        "wait_for_images": (
            frozenset({"sections"}),
            frozenset({"images", "sections"}),
        ),
        "assembler": (
            frozenset({"code_blocks", "images", "outline", "sections"}),
            frozenset({"outline"}),
        ),
    }


def test_node_contract_rejects_invalid_ingress_before_handler_runs():
    called = False

    def handler(state):
        nonlocal called
        called = True
        return state

    wrapped = wrap_node_state_contract("writer", handler)

    with pytest.raises(StateContractError) as raised:
        wrapped({"outline": {"sections": []}})

    assert called is False
    assert raised.value.node == "writer"
    assert raised.value.direction == "ingress"
    assert raised.value.field == "outline"


def test_node_contract_rejects_invalid_egress():
    wrapped = wrap_node_state_contract(
        "writer",
        lambda state: {**state, "sections": [{"id": 1}]},
    )

    with pytest.raises(StateContractError) as raised:
        wrapped({"outline": VALID_OUTLINE})

    assert raised.value.node == "writer"
    assert raised.value.direction == "egress"
    assert raised.value.field == "sections"


def test_node_contract_normalizes_valid_result_to_plain_json_values():
    wrapped = wrap_node_state_contract(
        "writer",
        lambda state: {
            **state,
            "sections": [
                {
                    "id": "intro",
                    "title": "Intro",
                    "content": "Body",
                    "extension": "kept",
                }
            ],
        },
    )

    result = wrapped({"outline": VALID_OUTLINE})

    assert isinstance(result["outline"], dict)
    assert isinstance(result["sections"], list)
    assert result["sections"][0]["extension"] == "kept"
    json.dumps(result)


def test_node_without_stable_contract_is_unchanged():
    state = {"topic": "Contracts"}
    wrapped = wrap_node_state_contract("unregistered", lambda value: value)

    assert wrapped(state) is state
