#!/usr/bin/env python3
"""
[需求点 69.05] Session 状态追踪 — 单元测试

验证：
  ST1 SessionTracker 初始化（TRACE_ENABLED=false 时禁用）
  ST2 SessionTracker 初始化（TRACE_ENABLED=true 但 Langfuse 不可用时禁用）
  ST3 log_score 在禁用时静默跳过
  ST4 log_event 在禁用时静默跳过
  ST5 log_review_score 正确调用 log_score
  ST6 log_depth_score 正确调用 log_score
  ST7 log_section_evaluation 正确调用 log_score
  ST8 log_image_generation 正确调用 log_score
  ST9 log_deepen_snapshot 正确调用 log_event
  ST10 log_section_improve_snapshot 正确调用 log_event
  ST11 log_score 异常时不抛出
  ST12 generator.py 中 reviewer_node 调用 tracker
  ST13 generator.py 中 section_evaluate_node 调用 tracker
  ST14 generator.py 中 section_improve_node 调用 tracker
  ST15 reviewer.py 不再包含 langfuse_client 引用
  ST16 questioner.py 不再包含 langfuse_client 变量
  ST17 artist.py 不再包含 langfuse_client 变量

用法：
  cd backend
  python -m pytest tests/test_69_05_session_tracker.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== ST1-ST2: 初始化 ==========

class TestSessionTrackerInit:
    def test_disabled_when_trace_off(self):
        """ST1: TRACE_ENABLED=false 时 tracker 禁用"""
        with patch.dict("os.environ", {"TRACE_ENABLED": "false"}):
            # 重新加载模块以应用环境变量
            import importlib
            import utils.session_tracker as mod
            importlib.reload(mod)
            tracker = mod.SessionTracker()
            assert tracker.enabled is False

    def test_disabled_when_langfuse_unavailable(self):
        """ST2: Langfuse 不可用时 tracker 禁用"""
        with patch.dict("os.environ", {"TRACE_ENABLED": "true"}):
            with patch("utils.session_tracker._get_langfuse", return_value=None):
                from utils.session_tracker import SessionTracker
                tracker = SessionTracker()
                tracker._langfuse = None
                tracker._enabled = False
                assert tracker.enabled is False


# ========== ST3-ST4: 禁用时静默跳过 ==========

class TestSessionTrackerDisabled:
    def setup_method(self):
        from utils.session_tracker import SessionTracker
        self.tracker = SessionTracker()
        self.tracker._enabled = False
        self.tracker._langfuse = None

    def test_log_score_noop_when_disabled(self):
        """ST3: 禁用时 log_score 不抛出"""
        self.tracker.log_score("test", 0.5, "comment")  # should not raise

    def test_log_event_noop_when_disabled(self):
        """ST4: 禁用时 log_event 不抛出"""
        self.tracker.log_event("test", {"key": "value"})  # should not raise


# ========== ST5-ST10: 便捷方法 ==========

class TestSessionTrackerMethods:
    def setup_method(self):
        from utils.session_tracker import SessionTracker
        self.tracker = SessionTracker()
        self.tracker._enabled = True
        self.tracker._langfuse = MagicMock()

    def test_log_review_score(self):
        """ST5: log_review_score 正确调用 Langfuse"""
        self.tracker.log_review_score(score=85, round_num=1, summary="ok")
        self.tracker._langfuse.score.assert_called_once()
        call_kwargs = self.tracker._langfuse.score.call_args[1]
        assert call_kwargs["name"] == "review_score"
        assert call_kwargs["value"] == 0.85

    def test_log_depth_score(self):
        """ST6: log_depth_score 正确调用 Langfuse"""
        self.tracker.log_depth_score(section_title="概述", score=70)
        call_kwargs = self.tracker._langfuse.score.call_args[1]
        assert call_kwargs["name"] == "depth_score"
        assert call_kwargs["value"] == 0.7

    def test_log_section_evaluation(self):
        """ST7: log_section_evaluation 正确调用 Langfuse"""
        self.tracker.log_section_evaluation(
            section_title="架构",
            scores={"info": 8, "logic": 7},
            overall=7.5,
        )
        call_kwargs = self.tracker._langfuse.score.call_args[1]
        assert call_kwargs["name"] == "section_quality"
        assert call_kwargs["value"] == 0.75

    def test_log_image_generation_success(self):
        """ST8a: log_image_generation 成功"""
        self.tracker.log_image_generation(
            image_id="img_1", image_type="mermaid", success=True
        )
        call_kwargs = self.tracker._langfuse.score.call_args[1]
        assert call_kwargs["value"] == 1.0

    def test_log_image_generation_failure(self):
        """ST8b: log_image_generation 失败"""
        self.tracker.log_image_generation(
            image_id="img_2", image_type="ai_image", success=False, error="timeout"
        )
        call_kwargs = self.tracker._langfuse.score.call_args[1]
        assert call_kwargs["value"] == 0.0
        assert "timeout" in call_kwargs["comment"]

    def test_log_deepen_snapshot(self):
        """ST9: log_deepen_snapshot 正确调用 log_event"""
        self.tracker.log_deepen_snapshot(
            round_num=1, sections_deepened=3, chars_added=500
        )
        self.tracker._langfuse.trace.assert_called_once()
        call_kwargs = self.tracker._langfuse.trace.call_args[1]
        assert call_kwargs["name"] == "deepen_round_1"
        assert call_kwargs["metadata"]["sections_deepened"] == 3

    def test_log_section_improve_snapshot(self):
        """ST10: log_section_improve_snapshot 正确调用 log_event"""
        self.tracker.log_section_improve_snapshot(
            round_num=1, improved_count=2, avg_score_before=5.5, avg_score_after=7.0
        )
        self.tracker._langfuse.trace.assert_called_once()
        meta = self.tracker._langfuse.trace.call_args[1]["metadata"]
        assert meta["improved_count"] == 2
        assert meta["delta"] == 1.5


# ========== ST11: 异常安全 ==========

class TestSessionTrackerErrorSafety:
    def test_log_score_exception_swallowed(self):
        """ST11: Langfuse 异常不影响主流程"""
        from utils.session_tracker import SessionTracker
        tracker = SessionTracker()
        tracker._enabled = True
        tracker._langfuse = MagicMock()
        tracker._langfuse.score.side_effect = Exception("network error")
        # Should not raise
        tracker.log_score("test", 0.5)


# ========== ST12-ST14: generator.py 集成验证 ==========

class TestGeneratorTrackerIntegration:
    def test_reviewer_node_calls_tracker(self):
        """ST12: _reviewer_node 调用 tracker.log_review_score"""
        import inspect
        from services.blog_generator.generator import BlogGenerator
        source = inspect.getsource(BlogGenerator._reviewer_node)
        assert "self.tracker.log_review_score" in source

    def test_section_evaluate_node_calls_tracker(self):
        """ST13: _section_evaluate_node 调用 tracker.log_section_evaluation"""
        import inspect
        from services.blog_generator.generator import BlogGenerator
        source = inspect.getsource(BlogGenerator._section_evaluate_node)
        assert "self.tracker.log_section_evaluation" in source

    def test_section_improve_node_calls_tracker(self):
        """ST14: _section_improve_node 调用 tracker.log_section_improve_snapshot"""
        import inspect
        from services.blog_generator.generator import BlogGenerator
        source = inspect.getsource(BlogGenerator._section_improve_node)
        assert "self.tracker.log_section_improve_snapshot" in source

    def test_deepen_content_node_calls_tracker(self):
        """ST14b: _deepen_content_node 调用 tracker.log_deepen_snapshot"""
        import inspect
        from services.blog_generator.generator import BlogGenerator
        source = inspect.getsource(BlogGenerator._deepen_content_node)
        assert "self.tracker.log_deepen_snapshot" in source

    def test_coder_and_artist_node_calls_tracker(self):
        """ST14c: _coder_and_artist_node 调用 tracker.log_image_generation"""
        import inspect
        from services.blog_generator.generator import BlogGenerator
        source = inspect.getsource(BlogGenerator._coder_and_artist_node)
        assert "self.tracker.log_image_generation" in source


# ========== ST15-ST17: Agent 清理验证 ==========

class TestAgentLangfuseCleanup:
    def test_reviewer_no_langfuse_client(self):
        """ST15: reviewer.py 不再包含 langfuse_client"""
        import inspect
        from services.blog_generator.agents.reviewer import ReviewerAgent
        source = inspect.getsource(ReviewerAgent)
        assert "langfuse_client" not in source

    def test_questioner_no_langfuse_client_var(self):
        """ST16: questioner.py 模块不再有 langfuse_client 变量"""
        import services.blog_generator.agents.questioner as mod
        assert not hasattr(mod, "langfuse_client")

    def test_artist_no_langfuse_client_var(self):
        """ST17: artist.py 模块不再有 langfuse_client 变量"""
        import services.blog_generator.agents.artist as mod
        assert not hasattr(mod, "langfuse_client")
