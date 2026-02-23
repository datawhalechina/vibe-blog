"""
LLM call structured logger -- records input/output/duration/tokens for LLM calls.
"""
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class LLMCallLogger:
    """LLM call logger that stores structured records."""

    def __init__(self):
        self._records: List[LLMCallRecord] = []

    def log_call(self, agent: str, model: str,
                 input_tokens: int = 0, output_tokens: int = 0,
                 duration_ms: float = 0.0, success: bool = True,
                 error: str = ""):
        record = LLMCallRecord(
            agent=agent, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            duration_ms=duration_ms, success=success, error=error,
        )
        self._records.append(record)
        if success:
            logger.info(
                f"LLM-CALL | agent={agent} model={model} "
                f"in={input_tokens} out={output_tokens} {duration_ms:.1f}ms"
            )
        else:
            logger.warning(
                f"LLM-FAIL | agent={agent} model={model} error={error}"
            )

    @contextmanager
    def track(self, agent: str, model: str):
        """Context manager that auto-times an LLM call."""
        start = time.time()
        result = {"input_tokens": 0, "output_tokens": 0}
        try:
            yield result
            duration = (time.time() - start) * 1000
            self.log_call(
                agent=agent, model=model,
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            self.log_call(
                agent=agent, model=model,
                duration_ms=duration, success=False, error=str(e),
            )
            raise

    def get_records(self, agent: str = "") -> List[LLMCallRecord]:
        if agent:
            return [r for r in self._records if r.agent == agent]
        return list(self._records)

    def get_summary(self) -> dict:
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_duration = sum(r.duration_ms for r in self._records)
        by_model: dict = {}
        for r in self._records:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "input": 0, "output": 0}
            by_model[r.model]["calls"] += 1
            by_model[r.model]["input"] += r.input_tokens
            by_model[r.model]["output"] += r.output_tokens
        return {
            "total_calls": len(self._records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_duration_ms": total_duration,
            "success_rate": (
                sum(1 for r in self._records if r.success)
                / max(len(self._records), 1)
            ),
            "by_model": by_model,
        }

    def clear(self):
        self._records.clear()
