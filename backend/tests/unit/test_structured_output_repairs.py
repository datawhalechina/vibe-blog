import pytest

from services.blog_generator.schemas.outputs import (
    HumanizerRewriteOutput,
    PlannerOutlineOutput,
)
from services.blog_generator.structured_output import (
    StructuredOutputError,
    parse_structured_output,
    repair_legacy_json,
    repair_planner_json,
)


def test_legacy_repair_accepts_incomplete_json_fence():
    raw = '```json\n{"replacements": []}'

    result = parse_structured_output(
        HumanizerRewriteOutput,
        raw,
        mode="compat",
        repair=repair_legacy_json,
    )

    assert result.replacements == []


def test_legacy_repair_normalizes_control_characters():
    raw = '{"replacements":[{"old":"line\nbreak","new":"fixed"}]}'

    result = parse_structured_output(
        HumanizerRewriteOutput,
        raw,
        mode="compat",
        repair=repair_legacy_json,
    )

    assert result.replacements[0].old == "line\nbreak"


def test_legacy_repair_normalizes_invalid_backslashes():
    raw = r'{"replacements":[{"old":"C:\temp\q","new":"fixed"}]}'

    result = parse_structured_output(
        HumanizerRewriteOutput,
        raw,
        mode="compat",
        repair=repair_legacy_json,
    )

    assert result.replacements[0].old == "C:\temp\\q"


def test_legacy_repair_does_not_extract_outer_braces_from_prose():
    raw = 'analysis before {"replacements": []} analysis after'

    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(
            HumanizerRewriteOutput,
            raw,
            mode="compat",
            repair=repair_legacy_json,
        )

    assert raised.value.kind == "decode"


@pytest.mark.parametrize(
    "raw",
    [
        'thinking first\n{"title":"T","sections":[{"title":"One"',
        '```json\n{"title":"T","sections":[{"title":"One"',
    ],
)
def test_planner_repair_handles_golden_truncation_cases(raw):
    result = parse_structured_output(
        PlannerOutlineOutput,
        raw,
        mode="compat",
        repair=repair_planner_json,
    )

    assert result.title == "T"
    assert [section.title for section in result.sections] == ["One"]


def test_planner_repair_rejects_content_without_json_object():
    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(
            PlannerOutlineOutput,
            "thinking without structured output",
            mode="compat",
            repair=repair_planner_json,
        )

    assert raised.value.kind == "decode"
