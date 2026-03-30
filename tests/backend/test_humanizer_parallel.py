"""
TDD 测试：Humanizer 并行化

验证 HumanizerAgent.run() 使用 ThreadPoolExecutor 并行处理 sections：
1. 多个 sections 被并行处理
2. 单个 section 异常不影响其他 sections
3. 结果按原始顺序回写
4. MAX_WORKERS 环境变量可配置
"""
import os
import time
import pytest
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor


def _make_section(title: str, content: str) -> dict:
    """构造测试用 section"""
    return {"title": title, "content": content}


def _make_score_response(total: int) -> dict:
    return {"score": {"total": total}}


def _make_rewrite_response(replacements: list) -> dict:
    return {"replacements": replacements}


# ==================== _process_section 提取验证 ====================

class TestProcessSectionExtracted:
    """验证 _process_section 方法已被提取为独立方法"""

    def test_process_section_method_exists(self):
        """_process_section 应作为 HumanizerAgent 的实例方法存在"""
        from services.blog_generator.agents.humanizer import HumanizerAgent
        assert hasattr(HumanizerAgent, '_process_section'), \
            "_process_section 方法应存在于 HumanizerAgent"

    def test_process_section_returns_dict_with_required_keys(self):
        """_process_section 返回包含 idx, section, status 的 dict"""
        from services.blog_generator.agents.humanizer import HumanizerAgent
        mock_llm = MagicMock()
        # score returns low score -> triggers rewrite
        mock_llm.chat.side_effect = [
            '{"score": {"total": 20}}',       # score
            '{"replacements": [{"old": "AI is", "new": "AI was"}]}',  # rewrite
            '{"score": {"total": 45}}',        # rescore
        ]
        agent = HumanizerAgent(mock_llm)
        section = _make_section("Test", "AI is great content here")
        result = agent._process_section(0, section, "technical-beginner", 1)

        assert isinstance(result, dict)
        assert result["idx"] == 0
        assert result["status"] in ("rewritten", "skipped")
        assert "section" in result

    def test_process_section_skipped_when_score_high(self):
        """评分高于阈值时 status 应为 skipped"""
        from services.blog_generator.agents.humanizer import HumanizerAgent

        mock_llm = MagicMock()
        mock_llm.chat.return_value = '{"score": {"total": 45}}'
        agent = HumanizerAgent(mock_llm)
        section = _make_section("Test", "Some human-like content here")
        result = agent._process_section(0, section, "technical-beginner", 1)

        assert result["status"] == "skipped"
        assert result["idx"] == 0


# ==================== 并行执行验证 ====================

class TestParallelExecution:
    """验证 run() 使用 ThreadPoolExecutor 并行处理"""

    def test_sections_processed_concurrently(self):
        """多个 sections 应并行处理，总耗时远小于串行耗时"""
        from services.blog_generator.agents.humanizer import HumanizerAgent

        DELAY = 0.3  # 每个 section 模拟延迟
        NUM_SECTIONS = 4

        original_chat = None

        def slow_chat(**kwargs):
            time.sleep(DELAY)
            msg = kwargs.get("messages", [{}])[0].get("content", "")
            if "caller" in kwargs:
                return '{"replacements": [{"old": "AI is", "new": "AI was"}]}'
            return '{"score": {"total": 45}}'

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = slow_chat

        agent = HumanizerAgent(mock_llm)
        sections = [
            _make_section(f"Section {i}", f"AI is great content number {i}")
            for i in range(NUM_SECTIONS)
        ]
        state = {"sections": sections, "audience_adaptation": "technical-beginner"}

        start = time.time()
        result = agent.run(state)
        elapsed = time.time() - start

        # 串行需要 NUM_SECTIONS * DELAY 秒（至少 1.2s），并行应远小于此
        serial_time = NUM_SECTIONS * DELAY
        assert elapsed < serial_time * 0.8, \
            f"并行处理耗时 {elapsed:.2f}s 应远小于串行 {serial_time:.2f}s"

    def test_results_in_original_order(self):
        """并行处理后结果应按原始 section 顺序回写"""
        from services.blog_generator.agents.humanizer import HumanizerAgent

        call_count = {"n": 0}

        def mock_chat(**kwargs):
            if "caller" in kwargs:
                return '{"replacements": [{"old": "placeholder", "new": "replaced"}]}'
            return '{"score": {"total": 20}}'

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = mock_chat

        agent = HumanizerAgent(mock_llm)
        sections = [
            _make_section(f"Section {i}", f"placeholder content for section {i}")
            for i in range(3)
        ]
        state = {"sections": sections}

        result = agent.run(state)
        result_sections = result["sections"]

        # 验证顺序：每个 section 的 title 应保持原始顺序
        for i, sec in enumerate(result_sections):
            assert sec["title"] == f"Section {i}", \
                f"Section {i} 顺序错乱: got {sec['title']}"


# ==================== 异常隔离验证 ====================

class TestExceptionIsolation:
    """验证单个 section 异常不影响其他 sections"""

    def test_one_section_error_others_succeed(self):
        """一个 section 处理异常时，其他 sections 仍正常处理"""
        from services.blog_generator.agents.humanizer import HumanizerAgent

        call_idx = {"n": 0}

        def mock_chat(**kwargs):
            msg = kwargs.get("messages", [{}])[0].get("content", "")
            # 对包含 "FAIL" 的 section 抛异常
            if "FAIL_THIS" in msg:
                raise RuntimeError("Simulated LLM failure")
            if "caller" in kwargs:
                return '{"replacements": [{"old": "good", "new": "great"}]}'
            return '{"score": {"total": 45}}'

        mock_llm = MagicMock()
        mock_llm.chat.side_effect = mock_chat

        agent = HumanizerAgent(mock_llm)
        sections = [
            _make_section("OK-0", "good content zero"),
            _make_section("FAIL-1", "FAIL_THIS content one"),
            _make_section("OK-2", "good content two"),
        ]
        state = {"sections": sections}

        result = agent.run(state)
        result_sections = result["sections"]

        # section 0 和 2 应正常处理
        assert result_sections[0]["title"] == "OK-0"
        assert result_sections[2]["title"] == "OK-2"
        # 不应因为 section 1 的异常而导致整个 run() 崩溃
        assert len(result_sections) == 3


# ==================== MAX_WORKERS 配置验证 ====================

class TestMaxWorkersConfig:
    """验证 HUMANIZER_MAX_WORKERS 环境变量"""

    def test_max_workers_from_env(self):
        """MAX_WORKERS 应从环境变量读取"""
        from services.blog_generator.agents.humanizer import MAX_WORKERS as default_workers
        assert isinstance(default_workers, int)
        assert default_workers > 0

    def test_max_workers_default_is_4(self):
        """默认 MAX_WORKERS 应为 4"""
        # 清除环境变量后检查默认值
        with patch.dict(os.environ, {}, clear=False):
            if 'HUMANIZER_MAX_WORKERS' in os.environ:
                del os.environ['HUMANIZER_MAX_WORKERS']
            # 重新导入以获取默认值
            import importlib
            import services.blog_generator.agents.humanizer as mod
            importlib.reload(mod)
            assert mod.MAX_WORKERS == 4
