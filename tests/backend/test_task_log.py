"""
37.08 结构化任务日志 — 单元测试
"""
import json
import time
from pathlib import Path
from unittest.mock import patch

from services.blog_generator.utils.task_log import (
    StepLog, BlogTaskLog, StepTimer,
)


# ============ StepLog 测试 ============

class TestStepLog:
    def test_defaults(self):
        s = StepLog()
        assert s.agent == ""
        assert s.action == ""
        assert s.level == "info"
        assert s.duration_ms == 0
        assert s.tokens == {"input": 0, "output": 0}

    def test_with_values(self):
        s = StepLog(agent="writer", action="write_section", duration_ms=5000,
                     tokens={"input": 100, "output": 50})
        assert s.agent == "writer"
        assert s.tokens["input"] == 100


# ============ BlogTaskLog 测试 ============

class TestBlogTaskLog:
    def test_auto_init(self):
        log = BlogTaskLog(topic="test topic")
        assert log.task_id.startswith("blog_")
        assert log.start_time != ""
        assert log.status == "running"
        assert log.topic == "test topic"

    def test_log_step_basic(self):
        log = BlogTaskLog()
        log.log_step("writer", "write_section", detail="section 1",
                      duration_ms=5000, tokens={"input": 100, "output": 50})
        assert len(log.steps) == 1
        assert log.steps[0].agent == "writer"
        assert log.total_tokens["input"] == 100
        assert log.total_tokens["output"] == 50
        assert log.total_duration_ms == 5000

    def test_log_step_agent_stats(self):
        log = BlogTaskLog()
        log.log_step("writer", "write_section_1", duration_ms=3000,
                      tokens={"input": 100, "output": 50})
        log.log_step("writer", "write_section_2", duration_ms=4000,
                      tokens={"input": 200, "output": 80})
        log.log_step("reviewer", "review", duration_ms=2000,
                      tokens={"input": 300, "output": 100})

        assert log.agent_stats["writer"]["steps"] == 2
        assert log.agent_stats["writer"]["duration_ms"] == 7000
        assert log.agent_stats["writer"]["tokens_input"] == 300
        assert log.agent_stats["reviewer"]["steps"] == 1

    def test_log_step_detail_truncation(self):
        log = BlogTaskLog()
        long_detail = "x" * 1000
        log.log_step("writer", "test", detail=long_detail)
        assert len(log.steps[0].detail) == 500

    def test_log_step_no_tokens(self):
        log = BlogTaskLog()
        log.log_step("planner", "generate_outline", duration_ms=1000)
        assert log.total_tokens["input"] == 0
        assert log.total_tokens["output"] == 0

    def test_complete(self):
        log = BlogTaskLog()
        log.complete(score=8.5, word_count=6500, revision_rounds=2)
        assert log.status == "completed"
        assert log.end_time != ""
        assert log.final_score == 8.5
        assert log.word_count == 6500
        assert log.revision_rounds == 2

    def test_fail(self):
        log = BlogTaskLog()
        log.fail("something went wrong")
        assert log.status == "failed"
        assert log.end_time != ""
        assert len(log.steps) == 1
        assert log.steps[0].level == "error"

    def test_save(self, tmp_path):
        log = BlogTaskLog(topic="test save")
        log.log_step("writer", "test", duration_ms=100)
        log.complete()

        path = log.save(logs_dir=str(tmp_path))
        assert Path(path).exists()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["topic"] == "test save"
        assert data["status"] == "completed"
        assert len(data["steps"]) == 1

    def test_get_summary(self):
        log = BlogTaskLog(topic="summary test")
        log.log_step("writer", "write", duration_ms=5000,
                      tokens={"input": 1000, "output": 500})
        log.complete(score=8.0, word_count=3000, revision_rounds=1)

        summary = log.get_summary()
        assert "summary test" in summary
        assert "completed" in summary
        assert "writer" in summary
        assert "8.0/10" in summary


# ============ StepTimer 测试 ============

class TestStepTimer:
    def test_basic_timing(self):
        log = BlogTaskLog()
        with StepTimer(log, "writer", "write_section"):
            time.sleep(0.05)

        assert len(log.steps) == 1
        assert log.steps[0].agent == "writer"
        assert log.steps[0].action == "write_section"
        assert log.steps[0].duration_ms >= 40  # at least ~50ms
        assert log.steps[0].level == "info"

    def test_error_recording(self):
        log = BlogTaskLog()
        try:
            with StepTimer(log, "reviewer", "review"):
                raise ValueError("bad review")
        except ValueError:
            pass

        assert len(log.steps) == 1
        assert log.steps[0].level == "error"
        assert "bad review" in log.steps[0].detail

    def test_metadata_passthrough(self):
        log = BlogTaskLog()
        with StepTimer(log, "writer", "write", section_index=3):
            pass

        assert log.steps[0].metadata.get("section_index") == 3
