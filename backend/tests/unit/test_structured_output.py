import json
import logging
from types import MappingProxyType

import pytest
from pydantic import BaseModel, RootModel, field_validator

from services import blog_generator
from services.blog_generator.structured_output import (
    StructuredOutputError,
    parse_structured_output,
)


class ExampleOutput(BaseModel):
    name: str
    count: int


class CompatibleSource(BaseModel):
    name: str
    count: int


class SecretRejectingOutput(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject_value(cls, value):
        raise ValueError(f"rejected secret value {value}")


class IntegerDictionaryOutput(RootModel[dict[str, int]]):
    pass


def test_blog_generator_package_exposes_structured_output_contract():
    assert blog_generator.parse_structured_output is parse_structured_output
    assert blog_generator.StructuredOutputError is StructuredOutputError


@pytest.mark.parametrize(
    "raw",
    [
        '{"name": "alpha", "count": 2}',
        '```json\n{"name": "alpha", "count": 2}\n```',
        '```JSON\n{"name": "alpha", "count": 2}\n```',
        MappingProxyType({"name": "alpha", "count": 2}),
        CompatibleSource(name="alpha", count=2),
    ],
)
def test_parse_structured_output_accepts_supported_inputs(raw):
    result = parse_structured_output(ExampleOutput, raw)

    assert result == ExampleOutput(name="alpha", count=2)


def test_strict_mode_rejects_surrounding_text():
    raw = 'Result:\n```json\n{"name": "alpha", "count": 2}\n```\nDone.'

    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(ExampleOutput, raw)

    assert raised.value.kind == "decode"


def test_compat_mode_accepts_one_fenced_block_with_surrounding_text():
    raw = 'Result:\n```json\n{"name": "alpha", "count": "2"}\n```\nDone.'

    result = parse_structured_output(ExampleOutput, raw, mode="compat")

    assert result == ExampleOutput(name="alpha", count=2)


def test_compat_mode_rejects_multiple_fenced_blocks():
    raw = (
        '```json\n{"name": "alpha", "count": 1}\n```\n'
        '```json\n{"name": "beta", "count": 2}\n```'
    )

    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(ExampleOutput, raw, mode="compat")

    assert raised.value.kind == "decode"


def test_compat_mode_counts_non_json_fenced_blocks_as_ambiguous():
    raw = (
        '```json\n{"name": "alpha", "count": 1}\n```\n'
        '```python\nprint("ignored")\n```'
    )

    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(ExampleOutput, raw, mode="compat")

    assert raised.value.kind == "decode"
    assert raised.value.details == [
        {"type": "ambiguous_fenced_output", "count": 2}
    ]


def test_strict_mode_disables_pydantic_type_coercion():
    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(
            ExampleOutput,
            {"name": "alpha", "count": "2"},
        )

    assert raised.value.kind == "validation"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "not JSON",
        '{"name": "truncated", "count": 2',
        'prefix {"name": "alpha", "count": 2} suffix',
        None,
        ["unsupported"],
    ],
)
def test_decode_errors_are_classified(raw):
    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(ExampleOutput, raw)

    error = raised.value
    assert error.kind == "decode"
    assert error.model_name == "ExampleOutput"
    assert error.details


@pytest.mark.parametrize(
    "raw",
    [
        {"name": "missing count"},
        {"name": "wrong type", "count": {"nested": True}},
    ],
)
def test_validation_errors_are_classified_without_input_values(raw):
    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(ExampleOutput, raw)

    error = raised.value
    assert error.kind == "validation"
    assert error.model_name == "ExampleOutput"
    assert error.details
    assert all("input" not in detail for detail in error.details)


def test_custom_validation_error_details_are_json_safe_and_secret_free():
    secret = "TOP-SECRET-CONTENT"

    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(SecretRejectingOutput, {"value": secret})

    serialized_details = json.dumps(raised.value.details)
    assert secret not in serialized_details
    assert raised.value.details == [
        {
            "type": "value_error",
            "loc": ["<field>"],
            "message": "Field validation failed",
        }
    ]


def test_validation_error_location_does_not_expose_dynamic_input_key(caplog):
    secret = "TOP-SECRET-DICT-KEY"

    with caplog.at_level(
        logging.WARNING,
        logger="services.blog_generator.structured_output",
    ):
        with pytest.raises(StructuredOutputError) as raised:
            parse_structured_output(IntegerDictionaryOutput, {secret: "bad"})

    serialized_details = json.dumps(raised.value.details)
    assert secret not in serialized_details
    assert secret not in caplog.text
    assert raised.value.details == [
        {
            "type": "int_type",
            "loc": ["<field>"],
            "message": "Field validation failed",
        }
    ]


def test_explicit_repair_is_attempted_once_after_decode_failure():
    calls = []

    def close_object(raw):
        calls.append(raw)
        return f"{raw}}}"

    result = parse_structured_output(
        ExampleOutput,
        '{"name": "repaired", "count": 3',
        repair=close_object,
    )

    assert result == ExampleOutput(name="repaired", count=3)
    assert calls == ['{"name": "repaired", "count": 3']


def test_failed_repair_is_not_retried():
    calls = []

    def still_invalid(raw):
        calls.append(raw)
        return raw

    with pytest.raises(StructuredOutputError) as raised:
        parse_structured_output(
            ExampleOutput,
            '{"name": "truncated"',
            repair=still_invalid,
        )

    assert raised.value.kind == "decode"
    assert len(calls) == 1


def test_error_log_uses_bounded_redacted_preview(caplog):
    secret = "sk-super-secret-token-value"
    raw = (
        '{"api_key": "'
        + secret
        + '", "name": "'
        + ("private-user-content-" * 30)
    )

    with caplog.at_level(
        logging.WARNING,
        logger="services.blog_generator.structured_output",
    ):
        with pytest.raises(StructuredOutputError) as raised:
            parse_structured_output(ExampleOutput, raw)

    log_text = caplog.text
    assert secret not in log_text
    assert "[REDACTED]" in log_text
    assert len(log_text) < 600
    assert secret not in str(raised.value)


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        (
            "Authorization: Basic dXNlcjpwYXNzd29yZA==",
            "dXNlcjpwYXNzd29yZA==",
        ),
        ("password=plain-text-password", "plain-text-password"),
        (
            '{"api_key":"prefix\\\"still-secret-value", broken',
            "still-secret-value",
        ),
    ],
)
def test_error_log_omits_malformed_sensitive_preview(caplog, raw, secret):
    with caplog.at_level(
        logging.WARNING,
        logger="services.blog_generator.structured_output",
    ):
        with pytest.raises(StructuredOutputError):
            parse_structured_output(ExampleOutput, raw)

    assert secret not in caplog.text
    assert "preview=[REDACTED]" in caplog.text
