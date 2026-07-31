"""Runtime contracts for stable, checkpointed ``SharedState`` payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Literal, Optional, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from .outputs import (
    AudienceAnalysis,
    CodeBlock,
    ConsistencyIssue,
    DepthVaguePoint,
    ImageResource,
    InstructionalAnalysis,
    KnowledgeGap,
    LearningObjective,
    PlannerOutlineOutput,
    ReviewIssue,
    SectionContent,
    VerbatimDataItem,
)


OutlinePayload: TypeAlias = Dict[str, Any]
SectionsPayload: TypeAlias = List[Dict[str, Any]]
CodeBlocksPayload: TypeAlias = List[Dict[str, Any]]
ImagesPayload: TypeAlias = List[Dict[str, Any]]
QuestionResultsPayload: TypeAlias = List[Dict[str, Any]]
ReviewIssuesPayload: TypeAlias = List[Dict[str, Any]]
InstructionalAnalysisPayload: TypeAlias = Dict[str, Any]
KnowledgeGapsPayload: TypeAlias = List[Dict[str, Any]]


class _StateSectionContent(SectionContent):
    model_config = ConfigDict(extra="allow")


class _StateCodeBlock(CodeBlock):
    model_config = ConfigDict(extra="allow")


class _StateImageResource(ImageResource):
    model_config = ConfigDict(extra="allow")

    render_method: Literal[
        "mermaid",
        "ai_image",
        "matplotlib",
        "enhanced_mermaid",
    ]


class _StateVaguePoint(DepthVaguePoint):
    model_config = ConfigDict(extra="allow")


class _StateQuestionResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    section_id: str
    is_detailed_enough: bool
    vague_points: List[_StateVaguePoint] = Field(default_factory=list)
    depth_score: int = Field(ge=0, le=100)


class _StateReviewIssue(ReviewIssue):
    model_config = ConfigDict(extra="allow")


class _StateConsistencyIssue(ConsistencyIssue):
    model_config = ConfigDict(extra="allow")


class _StateLearningObjective(LearningObjective):
    model_config = ConfigDict(extra="allow")


class _StateAudienceAnalysis(AudienceAnalysis):
    model_config = ConfigDict(extra="allow")


class _StateVerbatimDataItem(VerbatimDataItem):
    model_config = ConfigDict(extra="allow")


class _StateInstructionalAnalysis(InstructionalAnalysis):
    model_config = ConfigDict(extra="allow")

    learning_objectives: List[_StateLearningObjective] = Field(default_factory=list)
    audience: Optional[_StateAudienceAnalysis] = None
    verbatim_data: List[_StateVerbatimDataItem] = Field(default_factory=list)


class _StateKnowledgeGap(KnowledgeGap):
    model_config = ConfigDict(extra="allow")


_FIELD_ADAPTERS: Dict[str, TypeAdapter[Any]] = {
    "outline": TypeAdapter(Optional[PlannerOutlineOutput]),
    "sections": TypeAdapter(List[_StateSectionContent]),
    "code_blocks": TypeAdapter(List[_StateCodeBlock]),
    "images": TypeAdapter(List[_StateImageResource]),
    "question_results": TypeAdapter(List[_StateQuestionResult]),
    "review_issues": TypeAdapter(List[_StateReviewIssue | _StateConsistencyIssue]),
    "instructional_analysis": TypeAdapter(Optional[_StateInstructionalAnalysis]),
    "knowledge_gaps": TypeAdapter(List[_StateKnowledgeGap]),
}

STABLE_STATE_FIELDS = frozenset(_FIELD_ADAPTERS)


@dataclass(frozen=True)
class NodeStateContract:
    """Stable state fields read and written by a graph node."""

    reads: frozenset[str] = frozenset()
    writes: frozenset[str] = frozenset()


def _contract(*, reads: Iterable[str] = (), writes: Iterable[str] = ()) -> NodeStateContract:
    return NodeStateContract(frozenset(reads), frozenset(writes))


NODE_STATE_CONTRACTS: Dict[str, NodeStateContract] = {
    "researcher": _contract(writes={"instructional_analysis"}),
    "planner": _contract(
        reads={"instructional_analysis"},
        writes={"outline", "sections"},
    ),
    "writer": _contract(reads={"outline"}, writes={"sections"}),
    "check_knowledge": _contract(
        reads={"outline", "sections"},
        writes={"knowledge_gaps"},
    ),
    "refine_search": _contract(reads={"knowledge_gaps"}),
    "enhance_with_knowledge": _contract(
        reads={"sections", "knowledge_gaps"},
        writes={"sections", "knowledge_gaps"},
    ),
    "questioner": _contract(
        reads={"outline", "sections"},
        writes={"question_results"},
    ),
    "deepen_content": _contract(
        reads={"sections", "question_results"},
        writes={"sections"},
    ),
    "section_evaluate": _contract(reads={"sections"}),
    "section_improve": _contract(reads={"sections"}, writes={"sections"}),
    "coder_and_artist": _contract(
        reads={"sections"},
        writes={"code_blocks", "sections"},
    ),
    "cross_section_dedup": _contract(reads={"sections"}, writes={"sections"}),
    "consistency_check": _contract(reads={"outline", "sections"}),
    "reviewer": _contract(
        reads={"outline", "sections"},
        writes={"review_issues"},
    ),
    "revision": _contract(
        reads={"sections", "review_issues"},
        writes={"sections"},
    ),
    "factcheck": _contract(reads={"sections"}, writes={"sections"}),
    "text_cleanup": _contract(reads={"sections"}, writes={"sections"}),
    "humanizer": _contract(reads={"sections"}, writes={"sections"}),
    "wait_for_images": _contract(
        reads={"sections"},
        writes={"images", "sections"},
    ),
    "assembler": _contract(
        reads={"outline", "sections", "code_blocks", "images"},
        writes={"outline"},
    ),
}


class StateContractError(ValueError):
    """A stable state field failed validation at a graph boundary."""

    def __init__(
        self,
        *,
        field: str,
        node: str,
        direction: str,
        details: list[dict[str, Any]],
    ) -> None:
        self.field = field
        self.node = node
        self.direction = direction
        self.details = details
        super().__init__(
            f"Invalid {direction} state for node {node!r}, field {field!r}"
        )


def validate_state_fields(
    state: Mapping[str, Any],
    fields: Iterable[str],
    *,
    node: str,
    direction: str,
) -> dict[str, Any]:
    """Validate declared fields and normalize them to JSON-compatible values."""

    requested_fields = tuple(fields)
    unknown_fields = set(requested_fields) - STABLE_STATE_FIELDS
    if unknown_fields:
        unknown = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unknown stable state field: {unknown}")

    normalized_state = dict(state)
    for field in requested_fields:
        if field not in state:
            continue

        adapter = _FIELD_ADAPTERS[field]
        try:
            validated = adapter.validate_python(state[field], strict=True)
        except ValidationError as exc:
            raise StateContractError(
                field=field,
                node=node,
                direction=direction,
                details=exc.errors(include_input=False, include_url=False),
            ) from exc
        normalized_state[field] = adapter.dump_python(
            validated,
            mode="json",
            exclude_unset=True,
        )

    return normalized_state


def wrap_node_state_contract(
    node_name: str,
    fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Wrap a graph node with its declared stable state boundary checks."""

    contract = NODE_STATE_CONTRACTS.get(node_name)
    if contract is None:
        return fn

    @wraps(fn)
    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        normalized_input = validate_state_fields(
            state,
            contract.reads,
            node=node_name,
            direction="ingress",
        )
        result = fn(normalized_input)
        if not isinstance(result, Mapping):
            raise TypeError(f"Node {node_name!r} must return a mapping")
        return validate_state_fields(
            result,
            contract.writes,
            node=node_name,
            direction="egress",
        )

    return wrapped
