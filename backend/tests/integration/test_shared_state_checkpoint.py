import json

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from services.blog_generator.schemas.state import SharedState, create_initial_state
from services.blog_generator.schemas.state_contracts import (
    STABLE_STATE_FIELDS,
    validate_state_fields,
)


def _contains_model(value):
    if isinstance(value, BaseModel):
        return True
    if isinstance(value, dict):
        return any(_contains_model(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_model(item) for item in value)
    return False


def test_stable_state_payloads_survive_memory_saver_round_trip():
    state = create_initial_state("Checkpoint contracts", target_length="mini")
    state.update(
        {
            "outline": {
                "title": "Guide",
                "sections": [{"id": "intro", "title": "Intro"}],
            },
            "sections": [{"id": "intro", "title": "Intro", "content": "Body"}],
            "code_blocks": [
                {
                    "id": "code_1",
                    "code": "print(1)",
                    "output": "1",
                    "explanation": "Demo",
                }
            ],
            "images": [
                {
                    "id": "image_1",
                    "render_method": "mermaid",
                    "content": "flowchart TD",
                    "caption": "Flow",
                }
            ],
            "question_results": [
                {
                    "section_id": "intro",
                    "is_detailed_enough": True,
                    "depth_score": 90,
                    "vague_points": [],
                }
            ],
            "review_issues": [
                {
                    "section_id": "intro",
                    "issue_type": "logic",
                    "severity": "low",
                    "description": "Minor",
                    "suggestion": "Clarify",
                }
            ],
            "instructional_analysis": {
                "content_type": "tutorial",
                "learning_objectives": [],
                "verbatim_data": [],
            },
            "knowledge_gaps": [
                {
                    "gap_type": "missing_data",
                    "description": "Benchmark",
                    "suggested_query": "benchmark data",
                }
            ],
        }
    )
    normalized = validate_state_fields(
        state,
        STABLE_STATE_FIELDS,
        node="checkpoint",
        direction="egress",
    )

    graph = StateGraph(SharedState)
    graph.add_node("identity", lambda value: value)
    graph.add_edge(START, "identity")
    graph.add_edge("identity", END)
    app = graph.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "state-contract-round-trip"}}

    app.invoke(normalized, config)
    restored = app.get_state(config).values
    stable_payloads = {field: restored[field] for field in STABLE_STATE_FIELDS}

    validate_state_fields(
        restored,
        STABLE_STATE_FIELDS,
        node="checkpoint",
        direction="ingress",
    )
    json.dumps(stable_payloads)
    assert not _contains_model(stable_payloads)
