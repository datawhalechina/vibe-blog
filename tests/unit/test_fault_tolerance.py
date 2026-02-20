"""102.07 容错特性单元测试"""
import os
import sys
import time
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from utils.dangling_tool_call_fixer import fix_dangling_tool_calls
from utils.atomic_write import atomic_write
from utils.task_state import TaskStatus, TaskResult
from utils.safe_run import safe_run


# ---------------------------------------------------------------------------
# helpers — 轻量 mock，避免依赖 langchain 安装
# ---------------------------------------------------------------------------

class FakeToolMessage:
    """模拟 ToolMessage"""
    def __init__(self, tool_call_id, content=None, name=None, status=None):
        self.tool_call_id = tool_call_id
        self.content = content
        self.name = name
        self.status = status

class FakeAIMessage:
    """模拟 AIMessage"""
    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls or []

# monkey-patch isinstance checks used by fix_dangling_tool_calls
import utils.dangling_tool_call_fixer as _dtcf
_dtcf.ToolMessage = FakeToolMessage
_dtcf.AIMessage = FakeAIMessage


# ===================================================================
# 1. TestDanglingToolCallFixer
# ===================================================================

class TestDanglingToolCallFixer:
    def test_no_dangling_calls(self):
        ai = FakeAIMessage(tool_calls=[{'id': 'tc1', 'name': 'search'}])
        tool = FakeToolMessage(tool_call_id='tc1')
        assert fix_dangling_tool_calls([ai, tool]) == []

    def test_single_dangling_call(self):
        ai = FakeAIMessage(tool_calls=[{'id': 'tc1', 'name': 'search'}])
        patches = fix_dangling_tool_calls([ai])
        assert len(patches) == 1
        assert patches[0].tool_call_id == 'tc1'

    def test_multiple_dangling_calls(self):
        ai = FakeAIMessage(tool_calls=[
            {'id': 'tc1', 'name': 'a'},
            {'id': 'tc2', 'name': 'b'},
        ])
        patches = fix_dangling_tool_calls([ai])
        assert len(patches) == 2
        ids = {p.tool_call_id for p in patches}
        assert ids == {'tc1', 'tc2'}

    def test_partial_dangling(self):
        ai = FakeAIMessage(tool_calls=[
            {'id': 'tc1', 'name': 'a'},
            {'id': 'tc2', 'name': 'b'},
        ])
        tool = FakeToolMessage(tool_call_id='tc1')
        patches = fix_dangling_tool_calls([ai, tool])
        assert len(patches) == 1
        assert patches[0].tool_call_id == 'tc2'

    def test_empty_messages(self):
        assert fix_dangling_tool_calls([]) == []

    def test_dedup_patches(self):
        ai1 = FakeAIMessage(tool_calls=[{'id': 'tc1', 'name': 'x'}])
        ai2 = FakeAIMessage(tool_calls=[{'id': 'tc1', 'name': 'x'}])
        patches = fix_dangling_tool_calls([ai1, ai2])
        assert len(patches) == 1


# ===================================================================
# 2. TestAtomicWrite
# ===================================================================

class TestAtomicWrite:
    def test_basic_write(self, tmp_path):
        fp = str(tmp_path / "out.txt")
        atomic_write(fp, "hello")
        assert open(fp).read() == "hello"

    def test_overwrite_existing(self, tmp_path):
        fp = str(tmp_path / "out.txt")
        atomic_write(fp, "v1")
        atomic_write(fp, "v2")
        assert open(fp).read() == "v2"

    def test_creates_parent_dirs(self, tmp_path):
        fp = str(tmp_path / "a" / "b" / "out.txt")
        atomic_write(fp, "deep")
        assert open(fp).read() == "deep"


# ===================================================================
# 3. TestTaskStateMachine
# ===================================================================

class TestTaskStateMachine:
    def test_initial_state(self):
        tr = TaskResult(task_id="t1", node_name="writer")
        assert tr.status == TaskStatus.PENDING

    def test_state_transitions(self):
        tr = TaskResult(task_id="t1", node_name="writer")
        tr.status = TaskStatus.RUNNING
        assert tr.status == TaskStatus.RUNNING
        tr.status = TaskStatus.COMPLETED
        assert tr.status == TaskStatus.COMPLETED

    def test_duration_calculation(self):
        now = datetime.now()
        tr = TaskResult(
            task_id="t1", node_name="writer",
            started_at=now,
            completed_at=now + timedelta(seconds=3.5),
        )
        assert abs(tr.duration_seconds - 3.5) < 0.01

    def test_duration_none_when_incomplete(self):
        tr = TaskResult(task_id="t1", node_name="writer", started_at=datetime.now())
        assert tr.duration_seconds is None


# ===================================================================
# 4. TestEnhancedSafeRun
# ===================================================================

class _FakeNode:
    """用于测试 safe_run 装饰器的假节点"""

    @safe_run(default_return={"fallback": True})
    def ok_node(self, state):
        state["result"] = 42
        return state

    @safe_run(default_return={"fallback": True})
    def bad_node(self, state):
        raise RuntimeError("boom")

    call_count = 0

    @safe_run(default_return={}, max_retries=2, retry_delay=0.01)
    def flaky_node(self, state):
        self.call_count += 1
        if self.call_count < 3:
            raise RuntimeError("not yet")
        state["ok"] = True
        return state


class TestEnhancedSafeRun:
    def test_basic_safe_run(self):
        node = _FakeNode()
        result = node.ok_node({})
        assert result["result"] == 42

    def test_exception_returns_default(self):
        node = _FakeNode()
        result = node.bad_node({})
        assert result["fallback"] is True

    def test_retry_then_succeed(self):
        node = _FakeNode()
        node.call_count = 0
        result = node.flaky_node({})
        assert result.get("ok") is True
        assert node.call_count == 3


# ===================================================================
# 5. TestRecursionLimit
# ===================================================================

class TestRecursionLimit:
    """测试 _should_deepen 的硬限制逻辑（直接复现方法逻辑）"""

    @staticmethod
    def _should_deepen(state, max_questioning_rounds=3):
        MAX_DEEPEN_ROUNDS = 5
        if state.get('questioning_count', 0) >= MAX_DEEPEN_ROUNDS:
            return "continue"
        if not state.get('all_sections_detailed', True):
            if state.get('questioning_count', 0) < max_questioning_rounds:
                return "deepen"
        return "continue"

    def test_deepen_hard_limit(self):
        state = {'questioning_count': 5, 'all_sections_detailed': False}
        assert self._should_deepen(state, max_questioning_rounds=10) == "continue"

    def test_deepen_within_limit(self):
        state = {'questioning_count': 2, 'all_sections_detailed': False}
        assert self._should_deepen(state, max_questioning_rounds=5) == "deepen"


