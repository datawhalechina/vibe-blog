"""Typed parsing boundary for LLM structured output."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)
ParseMode = Literal["strict", "compat"]
RepairStrategy = Callable[[str], str | Mapping[str, Any] | BaseModel]

_WHOLE_FENCE_RE = re.compile(
    r"\A\s*```(?:json)?[ \t]*\r?\n(?P<body>.*?)\r?\n?```\s*\Z",
    re.IGNORECASE | re.DOTALL,
)
_ANY_FENCE_RE = re.compile(
    r"```(?P<label>[^\r\n`]*)\r?\n(?P<body>.*?)\r?\n?```",
    re.DOTALL,
)
_SENSITIVE_MARKER_RE = re.compile(
    r"(?i)(?:\b(?:api[_-]?key|authorization|access[_-]?token|token|secret|password)\b"
    r"|\b(?:basic|bearer)\s+\S+)"
)
_TOKEN_RE = re.compile(r"\b(?:sk|pk|AIza)-?[A-Za-z0-9_-]{8,}\b")
_PREVIEW_LIMIT = 240

__all__ = ["StructuredOutputError", "parse_structured_output"]


class StructuredOutputError(ValueError):
    """A structured-output failure with a stable decode/validation category."""

    def __init__(
        self,
        kind: Literal["decode", "validation"],
        model_name: str,
        details: list[dict[str, Any]],
    ) -> None:
        self.kind = kind
        self.model_name = model_name
        self.details = details
        super().__init__(f"Structured output {kind} failed for {model_name}")


class _DecodeFailure(Exception):
    def __init__(self, details: list[dict[str, Any]]) -> None:
        self.details = details


def parse_structured_output(
    model: type[ModelT],
    raw: str | Mapping[str, Any] | BaseModel,
    *,
    mode: ParseMode = "strict",
    repair: RepairStrategy | None = None,
) -> ModelT:
    """Decode and validate one LLM response as ``model``.

    Strict mode accepts pure JSON or a response fully wrapped in one JSON fence
    and disables Pydantic coercion. Compatibility mode additionally permits one
    fenced block surrounded by prose and uses normal Pydantic coercion. A repair
    strategy is opt-in and receives at most one attempt after a decode failure.
    """
    if mode not in {"strict", "compat"}:
        raise ValueError(f"Unsupported structured output mode: {mode}")
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise TypeError("model must be a Pydantic BaseModel class")

    model_name = model.__name__
    try:
        payload = _coerce_input(raw, mode)
    except _DecodeFailure as first_failure:
        if repair is None or not isinstance(raw, str):
            _raise_decode_error(model_name, raw, first_failure.details)

        try:
            repaired = repair(raw)
            payload = _coerce_input(repaired, mode)
        except _DecodeFailure as repair_failure:
            _raise_decode_error(model_name, raw, repair_failure.details)
        except Exception as exc:
            _raise_decode_error(
                model_name,
                raw,
                [{"type": "repair_error", "exception": type(exc).__name__}],
            )

    try:
        return model.model_validate(payload, strict=mode == "strict")
    except ValidationError as exc:
        details = _sanitize_validation_errors(exc)
        _log_failure("validation", model_name, raw)
        raise StructuredOutputError("validation", model_name, details) from None


def _coerce_input(
    raw: str | Mapping[str, Any] | BaseModel,
    mode: ParseMode,
) -> Any:
    if isinstance(raw, BaseModel):
        return raw.model_dump(mode="python")
    if isinstance(raw, Mapping):
        return dict(raw)
    if not isinstance(raw, str):
        raise _DecodeFailure(
            [{"type": "unsupported_input", "input_type": type(raw).__name__}]
        )

    candidate = _extract_json_text(raw, mode)
    if not candidate:
        raise _DecodeFailure([{"type": "empty_input"}])
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise _DecodeFailure(
            [
                {
                    "type": "json_decode",
                    "line": exc.lineno,
                    "column": exc.colno,
                    "position": exc.pos,
                }
            ]
        ) from None


def _extract_json_text(raw: str, mode: ParseMode) -> str:
    stripped = raw.strip()
    fenced_blocks = list(_ANY_FENCE_RE.finditer(stripped))
    if mode == "compat" and len(fenced_blocks) > 1:
        raise _DecodeFailure(
            [{"type": "ambiguous_fenced_output", "count": len(fenced_blocks)}]
        )

    whole_fence = _WHOLE_FENCE_RE.fullmatch(stripped)
    if whole_fence and len(fenced_blocks) == 1:
        return whole_fence.group("body").strip()
    if mode == "strict":
        return stripped

    if len(fenced_blocks) == 1:
        fenced_block = fenced_blocks[0]
        if fenced_block.group("label").strip().lower() in {"", "json"}:
            return fenced_block.group("body").strip()
        raise _DecodeFailure([{"type": "unsupported_fenced_output"}])
    return stripped


def _raise_decode_error(
    model_name: str,
    raw: Any,
    details: list[dict[str, Any]],
) -> None:
    _log_failure("decode", model_name, raw)
    raise StructuredOutputError("decode", model_name, details) from None


def _sanitize_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    details = []
    for error in exc.errors(include_url=False, include_input=False):
        location = [
            "<field>"
            if isinstance(part, str)
            else "<index>"
            if isinstance(part, int)
            else "<location>"
            for part in error.get("loc", ())
        ]
        details.append(
            {
                "type": str(error.get("type", "validation_error")),
                "loc": location,
                "message": "Field validation failed",
            }
        )
    return details


def _log_failure(kind: str, model_name: str, raw: Any) -> None:
    logger.warning(
        "Structured output %s failed: model=%s preview=%s",
        kind,
        model_name,
        _safe_preview(raw),
    )


def _safe_preview(raw: Any) -> str:
    if isinstance(raw, BaseModel):
        raw = raw.model_dump(mode="json")
    if isinstance(raw, Mapping):
        try:
            text = json.dumps(dict(raw), ensure_ascii=False, default=str)
        except Exception:
            text = f"<{type(raw).__name__}>"
    elif isinstance(raw, str):
        text = raw
    else:
        text = f"<{type(raw).__name__}>"

    if _SENSITIVE_MARKER_RE.search(text) or _TOKEN_RE.search(text):
        return "[REDACTED]"

    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > _PREVIEW_LIMIT:
        return f"{text[:_PREVIEW_LIMIT]}..."
    return text
