"""Tests for LLM call structured logger (1003.26)."""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from utils.llm_call_logger import LLMCallLogger, LLMCallRecord


class TestLLMCallLogger:
    """Tests for LLMCallLogger."""

    def setup_method(self):
        self.logger = LLMCallLogger()

    # 1. log a successful call, verify record stored
    def test_log_call_success(self):
        self.logger.log_call(
            agent="writer", model="gpt-4",
            input_tokens=100, output_tokens=50, duration_ms=320.5,
        )
        records = self.logger.get_records()
        assert len(records) == 1
        r = records[0]
        assert r.agent == "writer"
        assert r.model == "gpt-4"
        assert r.input_tokens == 100
        assert r.output_tokens == 50
        assert r.duration_ms == 320.5
        assert r.success is True
        assert r.error == ""

    # 2. log a failed call with error
    def test_log_call_failure(self):
        self.logger.log_call(
            agent="searcher", model="gpt-3.5",
            duration_ms=150.0, success=False, error="timeout",
        )
        records = self.logger.get_records()
        assert len(records) == 1
        r = records[0]
        assert r.success is False
        assert r.error == "timeout"
        assert r.agent == "searcher"

    # 3. track() context manager auto-timing
    def test_track_context_manager(self):
        with self.logger.track(agent="planner", model="claude-3") as result:
            time.sleep(0.01)  # ~10ms
            result["input_tokens"] = 200
            result["output_tokens"] = 80

        records = self.logger.get_records()
        assert len(records) == 1
        r = records[0]
        assert r.agent == "planner"
        assert r.model == "claude-3"
        assert r.input_tokens == 200
        assert r.output_tokens == 80
        assert r.duration_ms >= 5  # at least some time passed
        assert r.success is True

    # 4. track() with exception — error recorded and re-raised
    def test_track_exception(self):
        with pytest.raises(ValueError, match="bad input"):
            with self.logger.track(agent="critic", model="gpt-4") as result:
                raise ValueError("bad input")

        records = self.logger.get_records()
        assert len(records) == 1
        r = records[0]
        assert r.success is False
        assert r.error == "bad input"
        assert r.agent == "critic"
        assert r.duration_ms >= 0

    # 5. get all records
    def test_get_records_all(self):
        self.logger.log_call(agent="a1", model="m1")
        self.logger.log_call(agent="a2", model="m2")
        self.logger.log_call(agent="a3", model="m1")
        assert len(self.logger.get_records()) == 3

    # 6. filter by agent name
    def test_get_records_by_agent(self):
        self.logger.log_call(agent="writer", model="gpt-4")
        self.logger.log_call(agent="searcher", model="gpt-4")
        self.logger.log_call(agent="writer", model="claude-3")

        writer_records = self.logger.get_records(agent="writer")
        assert len(writer_records) == 2
        assert all(r.agent == "writer" for r in writer_records)

    # 7. summary aggregation
    def test_get_summary(self):
        self.logger.log_call(agent="a1", model="gpt-4", input_tokens=100, output_tokens=50)
        self.logger.log_call(agent="a2", model="gpt-4", input_tokens=200, output_tokens=100)
        self.logger.log_call(agent="a3", model="claude-3", input_tokens=50, output_tokens=25, success=False, error="err")

        summary = self.logger.get_summary()
        assert summary["total_calls"] == 3
        assert summary["total_input_tokens"] == 350
        assert summary["total_output_tokens"] == 175
        assert summary["by_model"]["gpt-4"]["calls"] == 2
        assert summary["by_model"]["gpt-4"]["input"] == 300
        assert summary["by_model"]["gpt-4"]["output"] == 150
        assert summary["by_model"]["claude-3"]["calls"] == 1
        # 2 out of 3 succeeded
        assert abs(summary["success_rate"] - 2 / 3) < 0.01

    # 8. clear removes all records
    def test_clear(self):
        self.logger.log_call(agent="a1", model="m1")
        self.logger.log_call(agent="a2", model="m2")
        assert len(self.logger.get_records()) == 2
        self.logger.clear()
        assert len(self.logger.get_records()) == 0

    # 9. summary on empty logger returns zeros
    def test_summary_empty(self):
        summary = self.logger.get_summary()
        assert summary["total_calls"] == 0
        assert summary["total_input_tokens"] == 0
        assert summary["total_output_tokens"] == 0
        assert summary["total_duration_ms"] == 0
        assert summary["success_rate"] == 0
        assert summary["by_model"] == {}
