"""
37.08 性能聚合统计 — 单元测试
"""
import json
from pathlib import Path

from services.blog_generator.utils.task_log import BlogTaskLog
from services.blog_generator.utils.performance_summary import (
    BlogPerformanceSummary, _TaskLogProxy,
)


class TestBlogPerformanceSummary:
    def _make_task_log(self):
        log = BlogTaskLog(topic="test", target_length="medium")
        log.log_step("writer", "write_section_1", duration_ms=5000,
                      tokens={"input": 1000, "output": 500})
        log.log_step("writer", "write_section_2", duration_ms=3000,
                      tokens={"input": 800, "output": 400})
        log.log_step("reviewer", "review", duration_ms=2000,
                      tokens={"input": 500, "output": 200})
        log.log_step("artist", "draw_image", duration_ms=8000)
        log.log_step("researcher", "search", duration_ms=1500)
        return log

    def test_add_single_task(self):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())

        assert summary.total_tasks == 1
        assert summary.total_wall_time_ms == 19500
        assert summary.agent_breakdown["writer"]["steps"] == 2
        assert summary.agent_breakdown["writer"]["duration_ms"] == 8000
        assert summary.agent_breakdown["reviewer"]["steps"] == 1

    def test_add_multiple_tasks(self):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())
        summary.add_task_log(self._make_task_log())

        assert summary.total_tasks == 2
        assert summary.total_wall_time_ms == 39000
        assert summary.agent_breakdown["writer"]["steps"] == 4

    def test_cross_cutting_breakdown(self):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())

        # write_section → llm_call_ms, draw_image → image_gen_ms, search → search_api_ms
        assert summary.cross_cutting_breakdown["llm_call_ms"] == 10000  # 5000+3000+2000
        assert summary.cross_cutting_breakdown["image_gen_ms"] == 8000
        assert summary.cross_cutting_breakdown["search_api_ms"] == 1500

    def test_service_workload(self):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())

        assert summary.service_workload["llm_chat"] == 3  # 2 write + 1 review
        assert summary.service_workload["image_generate"] == 1
        assert summary.service_workload["search"] == 1

    def test_get_averages(self):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())
        summary.add_task_log(self._make_task_log())

        avg = summary.get_averages()
        assert avg["avg_wall_time_ms"] == 19500
        assert avg["avg_agent_breakdown"]["writer"]["avg_steps"] == 2

    def test_get_averages_empty(self):
        summary = BlogPerformanceSummary()
        assert summary.get_averages() == {}

    def test_get_report(self):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())

        report = summary.get_report()
        assert "1 个任务" in report
        assert "writer" in report
        assert "LLM 调用" in report

    def test_get_report_empty(self):
        summary = BlogPerformanceSummary()
        assert "暂无" in summary.get_report()

    def test_save_and_load(self, tmp_path):
        summary = BlogPerformanceSummary()
        summary.add_task_log(self._make_task_log())

        out = str(tmp_path / "perf.json")
        summary.save(out)

        with open(out, "r") as f:
            data = json.load(f)
        assert data["total_tasks"] == 1
        assert "agent_breakdown" in data

    def test_from_log_dir(self, tmp_path):
        # 先保存一个 task log
        log = self._make_task_log()
        log.complete()
        log.save(str(tmp_path))

        # 从目录读取聚合
        summary = BlogPerformanceSummary.from_log_dir(str(tmp_path))
        assert summary.total_tasks == 1
        assert summary.agent_breakdown["writer"]["steps"] == 2

    def test_from_log_dir_nonexistent(self):
        summary = BlogPerformanceSummary.from_log_dir("/nonexistent/path")
        assert summary.total_tasks == 0


class TestTaskLogProxy:
    def test_proxy_attributes(self):
        data = {
            "total_duration_ms": 5000,
            "agent_stats": {"writer": {"steps": 2, "duration_ms": 3000,
                                        "tokens_input": 100, "tokens_output": 50}},
            "target_length": "medium",
            "steps": [{"action": "write_section", "duration_ms": 3000}],
        }
        proxy = _TaskLogProxy(data)
        assert proxy.total_duration_ms == 5000
        assert proxy.agent_stats["writer"]["steps"] == 2
        assert len(proxy.steps) == 1


class TestClassifyAction:
    def test_llm_actions(self):
        assert BlogPerformanceSummary._classify_action("write_section_1") == "llm_call_ms"
        assert BlogPerformanceSummary._classify_action("review") == "llm_call_ms"
        assert BlogPerformanceSummary._classify_action("generate_outline") == "llm_call_ms"

    def test_search_actions(self):
        assert BlogPerformanceSummary._classify_action("search") == "search_api_ms"
        assert BlogPerformanceSummary._classify_action("research") == "search_api_ms"

    def test_image_actions(self):
        assert BlogPerformanceSummary._classify_action("draw_image") == "image_gen_ms"
        assert BlogPerformanceSummary._classify_action("artist_generate") == "image_gen_ms"

    def test_other_actions(self):
        assert BlogPerformanceSummary._classify_action("unknown_action") == "other_ms"
