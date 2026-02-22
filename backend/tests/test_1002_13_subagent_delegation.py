"""
1002.13 子代理委托系统 — 单元测试

覆盖：
- SubagentConfig 数据类
- SubagentRegistry 注册/查找/列表
- SubagentExecutor 同步/异步执行、超时、失败、事件回调
- SubagentLimitGuard 并发限制
- delegate_task 委托入口函数
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.subagents.config import SubagentConfig
from services.blog_generator.subagents.registry import (
    register_subagent, get_subagent_config, list_subagents, _registry,
)
from services.blog_generator.subagents.executor import (
    SubagentExecutor, get_background_task, _background_tasks, _background_tasks_lock,
)
from services.blog_generator.subagents.limit_guard import SubagentLimitGuard
from services.blog_generator.subagents.delegate import delegate_task
from services.blog_generator.parallel.executor import TaskStatus


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前清空注册表"""
    _registry.clear()
    yield
    _registry.clear()


@pytest.fixture(autouse=True)
def clean_background_tasks():
    """每个测试前清空后台任务"""
    with _background_tasks_lock:
        _background_tasks.clear()
    yield
    with _background_tasks_lock:
        _background_tasks.clear()


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat.return_value = "子代理执行结果：任务完成"
    return llm


@pytest.fixture
def researcher_config():
    return SubagentConfig(
        name="researcher",
        description="调研子代理",
        system_prompt="你是一个调研专家，负责搜索和整理资料。",
        timeout_seconds=60,
        max_turns=10,
    )


@pytest.fixture
def writer_config():
    return SubagentConfig(
        name="writer",
        description="写作子代理",
        system_prompt="你是一个写作专家。",
        timeout_seconds=120,
    )


# ==================== SubagentConfig Tests ====================

class TestSubagentConfig:
    """SubagentConfig 数据类测试"""

    def test_default_values(self):
        config = SubagentConfig(
            name="test",
            description="测试子代理",
            system_prompt="你是测试代理",
        )
        assert config.name == "test"
        assert config.model == "inherit"
        assert config.max_turns == 30
        assert config.timeout_seconds == 300
        assert config.disallowed_tools == ["delegate_task"]
        assert config.tools is None

    def test_custom_values(self):
        config = SubagentConfig(
            name="custom",
            description="自定义",
            system_prompt="prompt",
            tools=["search", "crawl"],
            model="gpt-4o-mini",
            max_turns=10,
            timeout_seconds=60,
        )
        assert config.tools == ["search", "crawl"]
        assert config.model == "gpt-4o-mini"
        assert config.max_turns == 10

    def test_disallowed_tools_prevents_recursion(self):
        config = SubagentConfig(
            name="test", description="", system_prompt="",
        )
        assert "delegate_task" in config.disallowed_tools


# ==================== SubagentRegistry Tests ====================

class TestSubagentRegistry:
    """子代理注册表测试"""

    def test_register_and_get(self, researcher_config):
        register_subagent(researcher_config)
        found = get_subagent_config("researcher")
        assert found is not None
        assert found.name == "researcher"

    def test_get_nonexistent(self):
        assert get_subagent_config("nonexistent") is None

    def test_list_subagents(self, researcher_config, writer_config):
        register_subagent(researcher_config)
        register_subagent(writer_config)
        agents = list_subagents()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"researcher", "writer"}

    def test_register_overwrites(self, researcher_config):
        register_subagent(researcher_config)
        updated = SubagentConfig(
            name="researcher",
            description="更新后的调研子代理",
            system_prompt="新 prompt",
        )
        register_subagent(updated)
        found = get_subagent_config("researcher")
        assert found.description == "更新后的调研子代理"

    def test_list_empty(self):
        assert list_subagents() == []


# ==================== SubagentExecutor Sync Tests ====================

class TestSubagentExecutorSync:
    """同步执行测试"""

    def test_execute_success(self, mock_llm, researcher_config):
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        result = executor.execute("搜索 AI Agent 最新进展")
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "子代理执行结果：任务完成"
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    def test_execute_failure(self, mock_llm, researcher_config):
        mock_llm.chat.side_effect = RuntimeError("LLM 服务不可用")
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        result = executor.execute("搜索任务")
        assert result.status == TaskStatus.FAILED
        assert "LLM 服务不可用" in result.error

    def test_execute_builds_correct_messages(self, mock_llm, researcher_config):
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        executor.execute("测试 prompt")
        mock_llm.chat.assert_called_once()
        call_kwargs = mock_llm.chat.call_args
        messages = call_kwargs[1]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == researcher_config.system_prompt
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "测试 prompt"

    def test_execute_has_trace_id(self, mock_llm, researcher_config):
        executor = SubagentExecutor(
            config=researcher_config, llm_client=mock_llm, trace_id="abc123",
        )
        assert executor.trace_id == "abc123"

    def test_execute_auto_generates_trace_id(self, mock_llm, researcher_config):
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        assert executor.trace_id is not None
        assert len(executor.trace_id) == 8


# ==================== SubagentExecutor Async Tests ====================

class TestSubagentExecutorAsync:
    """异步执行测试"""

    def test_async_returns_task_id(self, mock_llm, researcher_config):
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        task_id = executor.execute_async("异步调研任务")
        assert isinstance(task_id, str)
        assert len(task_id) == 8

    def test_async_completes(self, mock_llm, researcher_config):
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        task_id = executor.execute_async("异步调研任务")
        # 等待异步完成
        for _ in range(20):
            result = get_background_task(task_id)
            if result and result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
            time.sleep(0.2)
        result = get_background_task(task_id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    def test_async_event_callback(self, mock_llm, researcher_config):
        events = []
        executor = SubagentExecutor(
            config=researcher_config,
            llm_client=mock_llm,
            on_event=lambda e: events.append(e),
        )
        task_id = executor.execute_async("事件回调测试")
        for _ in range(20):
            result = get_background_task(task_id)
            if result and result.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.2)
        assert len(events) >= 1
        assert events[-1]["type"] == "subtask_completed"
        assert events[-1]["task_id"] == task_id

    def test_async_custom_task_id(self, mock_llm, researcher_config):
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        task_id = executor.execute_async("任务", task_id="custom01")
        assert task_id == "custom01"

    def test_async_failure(self, mock_llm, researcher_config):
        mock_llm.chat.side_effect = RuntimeError("LLM 崩溃")
        executor = SubagentExecutor(config=researcher_config, llm_client=mock_llm)
        task_id = executor.execute_async("失败任务")
        for _ in range(20):
            result = get_background_task(task_id)
            if result and result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
            time.sleep(0.2)
        result = get_background_task(task_id)
        assert result.status == TaskStatus.FAILED
        assert "LLM 崩溃" in result.error


# ==================== SubagentLimitGuard Tests ====================

class TestSubagentLimitGuard:
    """并发限制守卫测试"""

    def test_default_max_concurrent(self):
        guard = SubagentLimitGuard()
        assert guard.max_concurrent == 3

    def test_custom_max_concurrent(self):
        guard = SubagentLimitGuard(max_concurrent=5)
        assert guard.max_concurrent == 5

    def test_acquire_and_release(self):
        guard = SubagentLimitGuard(max_concurrent=2)
        assert guard.acquire(timeout=1) is True
        assert guard.acquire(timeout=1) is True
        assert guard.active_count == 2
        guard.release()
        assert guard.active_count == 1
        guard.release()
        assert guard.active_count == 0

    def test_acquire_blocks_at_limit(self):
        guard = SubagentLimitGuard(max_concurrent=1)
        assert guard.acquire(timeout=1) is True
        # 第二次 acquire 应该超时
        assert guard.acquire(timeout=0.5) is False
        guard.release()
        # 释放后可以再次获取
        assert guard.acquire(timeout=1) is True


# ==================== delegate_task Tests ====================

class TestDelegateTask:
    """委托入口函数测试"""

    def test_delegate_success(self, mock_llm, researcher_config):
        register_subagent(researcher_config)
        result = delegate_task(
            subagent_name="researcher",
            task_prompt="搜索 AI 最新进展",
            llm_client=mock_llm,
        )
        assert result["status"] == "completed"
        assert result["result"] is not None

    def test_delegate_unknown_subagent(self, mock_llm):
        result = delegate_task(
            subagent_name="unknown",
            task_prompt="任务",
            llm_client=mock_llm,
        )
        assert result["status"] == "failed"
        assert "未找到" in result["error"] or "not found" in result["error"].lower()

    def test_delegate_with_sse_events(self, mock_llm, researcher_config):
        register_subagent(researcher_config)
        events = []
        result = delegate_task(
            subagent_name="researcher",
            task_prompt="搜索任务",
            llm_client=mock_llm,
            on_event=lambda e: events.append(e),
        )
        assert result["status"] == "completed"
        # 应该有 subtask_started 和 subtask_completed 事件
        event_types = [e["type"] for e in events]
        assert "subtask_started" in event_types
        assert "subtask_completed" in event_types

    def test_delegate_with_trace_id(self, mock_llm, researcher_config):
        register_subagent(researcher_config)
        result = delegate_task(
            subagent_name="researcher",
            task_prompt="任务",
            llm_client=mock_llm,
            trace_id="trace123",
        )
        assert result["status"] == "completed"
        assert result["trace_id"] == "trace123"
