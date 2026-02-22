"""
LLM 自动记忆提取 — 单元测试

测试 MemoryExtractor + MemoryExtractQueue 的核心功能：
- LLM 提取更新 writingProfile / topicHistory
- 置信度门控过滤低分事实
- 配置禁用时跳过提取
- 空消息返回 False
- LLM 返回非法 JSON 优雅降级
- max_facts 上限裁剪
- 去抖队列按 user_id 去重
- 不同用户不去重
"""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.memory.storage import MemoryStorage, create_empty_memory
from services.blog_generator.memory.config import BlogMemoryConfig


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture
def storage(tmp_path):
    return MemoryStorage(storage_path=str(tmp_path))


@pytest.fixture
def config():
    return BlogMemoryConfig(
        enabled=True,
        auto_extract_enabled=True,
        fact_confidence_threshold=0.7,
        max_facts=50,
    )


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 返回的结构化 JSON"""
    return json.dumps({
        "writingProfile": {
            "preferredStyle": {"summary": "深入浅出的技术写作", "shouldUpdate": True},
            "preferredAudience": {"summary": "中级 Python 开发者", "shouldUpdate": True},
            "preferredLength": {"summary": "", "shouldUpdate": False},
            "preferredImageStyle": {"summary": "", "shouldUpdate": False},
        },
        "topicHistory": {
            "recentTopics": {"summary": "AI Agent, LangGraph, RAG", "shouldUpdate": True},
            "topicClusters": {"summary": "", "shouldUpdate": False},
            "avoidTopics": {"summary": "", "shouldUpdate": False},
        },
        "qualityPreferences": {
            "revisionPatterns": {"summary": "", "shouldUpdate": False},
            "feedbackHistory": {"summary": "", "shouldUpdate": False},
        },
        "newFacts": [
            {"content": "偏好使用 Python 代码示例", "category": "preference", "confidence": 0.9},
            {"content": "关注 LangGraph 多智能体编排", "category": "knowledge", "confidence": 0.85},
            {"content": "可能对前端不太熟悉", "category": "context", "confidence": 0.4},
        ],
        "factsToRemove": [],
    })


# ── MemoryExtractor Tests ─────────────────────────────────


class TestMemoryExtractor:
    def test_extract_updates_writing_profile(self, storage, config, mock_llm_response):
        """LLM 提取应更新 writingProfile"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=mock_llm_response)
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            result = extractor.extract_and_update(
                "user_001",
                [{"role": "user", "content": "我喜欢深入浅出的风格"}],
                source="test",
            )
            assert result is True
            memory = storage.load("user_001")
            assert memory["writingProfile"]["preferredStyle"]["summary"] == "深入浅出的技术写作"
            assert memory["writingProfile"]["preferredAudience"]["summary"] == "中级 Python 开发者"

    def test_extract_updates_topic_history(self, storage, config, mock_llm_response):
        """LLM 提取应更新 topicHistory"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=mock_llm_response)
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            extractor.extract_and_update("user_001", [{"role": "user", "content": "test"}])
            memory = storage.load("user_001")
            assert memory["topicHistory"]["recentTopics"]["summary"] == "AI Agent, LangGraph, RAG"

    def test_confidence_threshold_filters_low_facts(self, storage, config, mock_llm_response):
        """低置信度事实应被过滤"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=mock_llm_response)
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            extractor.extract_and_update("user_001", [{"role": "user", "content": "test"}])
            memory = storage.load("user_001")
            # confidence 0.4 的事实应被过滤，只保留 0.9 和 0.85
            assert len(memory["facts"]) == 2
            assert all(f["confidence"] >= 0.7 for f in memory["facts"])

    def test_disabled_config_skips_extraction(self, storage):
        """禁用 auto_extract_enabled 时应跳过提取"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        config = BlogMemoryConfig(enabled=True, auto_extract_enabled=False)
        extractor = MemoryExtractor(storage, config)
        assert extractor.extract_and_update("u1", [{"role": "user", "content": "hi"}]) is False

    def test_disabled_memory_skips_extraction(self, storage):
        """禁用 enabled 时应跳过提取"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        config = BlogMemoryConfig(enabled=False, auto_extract_enabled=True)
        extractor = MemoryExtractor(storage, config)
        assert extractor.extract_and_update("u1", [{"role": "user", "content": "hi"}]) is False

    def test_empty_messages_returns_false(self, storage, config):
        """空消息列表应返回 False"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        extractor = MemoryExtractor(storage, config)
        assert extractor.extract_and_update("u1", []) is False

    def test_malformed_llm_response_handled(self, storage, config):
        """LLM 返回非法 JSON 应优雅降级"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="not valid json")
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            assert extractor.extract_and_update("u1", [{"role": "user", "content": "hi"}]) is False

    def test_markdown_wrapped_json_handled(self, storage, config):
        """LLM 返回 markdown 包裹的 JSON 应正确解析"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        wrapped = "```json\n" + json.dumps({
            "writingProfile": {},
            "topicHistory": {},
            "qualityPreferences": {},
            "newFacts": [
                {"content": "test fact", "category": "knowledge", "confidence": 0.9},
            ],
            "factsToRemove": [],
        }) + "\n```"

        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=wrapped)
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            result = extractor.extract_and_update("u1", [{"role": "user", "content": "test"}])
            assert result is True
            memory = storage.load("u1")
            assert len(memory["facts"]) == 1

    def test_max_facts_enforced(self, storage, config):
        """事实数量应不超过 max_facts"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        config.max_facts = 3
        # 预填充 2 条事实
        storage.add_fact("u1", "existing fact 1", confidence=0.8)
        storage.add_fact("u1", "existing fact 2", confidence=0.75)

        response = json.dumps({
            "writingProfile": {},
            "topicHistory": {},
            "qualityPreferences": {},
            "newFacts": [
                {"content": f"new fact {i}", "category": "knowledge", "confidence": 0.9}
                for i in range(5)
            ],
            "factsToRemove": [],
        })
        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=response)
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            extractor.extract_and_update("u1", [{"role": "user", "content": "test"}])
            memory = storage.load("u1")
            assert len(memory["facts"]) <= 3

    def test_facts_to_remove(self, storage, config):
        """factsToRemove 应删除指定事实"""
        from services.blog_generator.memory.extractor import MemoryExtractor

        fact_id = storage.add_fact("u1", "old fact", confidence=0.8)

        response = json.dumps({
            "writingProfile": {},
            "topicHistory": {},
            "qualityPreferences": {},
            "newFacts": [],
            "factsToRemove": [fact_id],
        })
        with patch.object(MemoryExtractor, '_get_llm') as mock_get:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content=response)
            mock_get.return_value = mock_llm

            extractor = MemoryExtractor(storage, config)
            extractor.extract_and_update("u1", [{"role": "user", "content": "test"}])
            memory = storage.load("u1")
            assert len(memory["facts"]) == 0


# ── MemoryExtractQueue Tests ──────────────────────────────


class TestMemoryExtractQueue:
    def test_debounce_batches_updates(self):
        """去抖应合并同一用户的多次更新"""
        from services.blog_generator.memory.extract_queue import MemoryExtractQueue

        queue = MemoryExtractQueue(debounce_seconds=1)
        mock_extractor = MagicMock()
        queue.set_extractor(mock_extractor)

        queue.add("u1", [{"role": "user", "content": "msg1"}])
        queue.add("u1", [{"role": "user", "content": "msg2"}])  # 覆盖 msg1
        queue.flush()

        # 应只调用一次，使用最新的 messages
        assert mock_extractor.extract_and_update.call_count == 1
        call_args = mock_extractor.extract_and_update.call_args
        assert call_args[0][1][0]["content"] == "msg2"

    def test_different_users_not_deduplicated(self):
        """不同用户的更新不应被去重"""
        from services.blog_generator.memory.extract_queue import MemoryExtractQueue

        queue = MemoryExtractQueue(debounce_seconds=1)
        mock_extractor = MagicMock()
        queue.set_extractor(mock_extractor)

        queue.add("u1", [{"role": "user", "content": "msg1"}])
        queue.add("u2", [{"role": "user", "content": "msg2"}])
        queue.flush()

        assert mock_extractor.extract_and_update.call_count == 2

    def test_pending_count(self):
        """pending_count 应反映队列大小"""
        from services.blog_generator.memory.extract_queue import MemoryExtractQueue

        queue = MemoryExtractQueue(debounce_seconds=60)
        assert queue.pending_count == 0
        queue.add("u1", [{"role": "user", "content": "msg1"}])
        assert queue.pending_count == 1
        queue.add("u2", [{"role": "user", "content": "msg2"}])
        assert queue.pending_count == 2
        # 同一用户覆盖，不增加
        queue.add("u1", [{"role": "user", "content": "msg3"}])
        assert queue.pending_count == 2
        # 清理 timer
        queue.flush()

    def test_no_extractor_logs_warning(self):
        """未设置 extractor 时 flush 不应崩溃"""
        from services.blog_generator.memory.extract_queue import MemoryExtractQueue

        queue = MemoryExtractQueue(debounce_seconds=1)
        queue.add("u1", [{"role": "user", "content": "msg1"}])
        queue.flush()  # 不应抛异常


# ── Prompt Formatting Tests ───────────────────────────────


class TestPromptFormatting:
    def test_format_conversation(self):
        """format_conversation 应正确格式化消息"""
        from services.blog_generator.memory.prompts import format_conversation

        messages = [
            {"role": "user", "content": "写一篇关于 AI 的文章"},
            {"role": "assistant", "content": "好的，我来帮你写"},
        ]
        result = format_conversation(messages)
        assert "用户" in result or "user" in result.lower()
        assert "AI" in result
        assert len(result) > 0

    def test_format_conversation_empty(self):
        """空消息列表应返回空字符串"""
        from services.blog_generator.memory.prompts import format_conversation

        assert format_conversation([]) == ""


# ── Config Enhancement Tests ──────────────────────────────


class TestConfigEnhancement:
    def test_auto_extract_enabled_default(self):
        """auto_extract_enabled 默认应为 True"""
        config = BlogMemoryConfig()
        assert config.auto_extract_enabled is True

    def test_model_name_default(self):
        """model_name 默认应为空字符串"""
        config = BlogMemoryConfig()
        assert config.model_name == ""

    def test_from_env_reads_new_fields(self):
        """from_env 应读取新增的环境变量"""
        with patch.dict(os.environ, {
            "MEMORY_AUTO_EXTRACT_ENABLED": "false",
            "MEMORY_MODEL_NAME": "gpt-4o-mini",
        }):
            config = BlogMemoryConfig.from_env()
            assert config.auto_extract_enabled is False
            assert config.model_name == "gpt-4o-mini"
