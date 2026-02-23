"""
TDD 测试 — 1003.04 动态主题队列 DynamicTopicQueue
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.services.topic_queue import (
    TopicStatus, TopicBlock, DynamicTopicQueue,
)


# ── TopicBlock 测试 ──

class TestTopicBlock:
    def test_creation_defaults(self):
        block = TopicBlock(block_id="block_1", sub_topic="AI Safety", overview="Overview")
        assert block.status == TopicStatus.PENDING
        assert block.iteration_count == 0
        assert block.search_traces == []

    def test_add_search_trace(self):
        block = TopicBlock(block_id="block_1", sub_topic="AI", overview="")
        old_updated = block.updated_at
        block.add_search_trace({"query": "AI safety", "summary": "Key findings..."})
        assert len(block.search_traces) == 1
        assert block.updated_at >= old_updated

    def test_get_all_summaries(self):
        block = TopicBlock(block_id="block_1", sub_topic="AI", overview="")
        block.add_search_trace({"query": "q1", "summary": "s1"})
        block.add_search_trace({"query": "q2", "summary": "s2"})
        summaries = block.get_all_summaries()
        assert "s1" in summaries
        assert "s2" in summaries

    def test_get_all_summaries_empty(self):
        block = TopicBlock(block_id="block_1", sub_topic="AI", overview="")
        assert block.get_all_summaries() == ""

    def test_serialization(self):
        block = TopicBlock(block_id="block_1", sub_topic="AI", overview="test")
        block.status = TopicStatus.COMPLETED
        data = block.to_dict()
        restored = TopicBlock.from_dict(data)
        assert restored.block_id == "block_1"
        assert restored.status == TopicStatus.COMPLETED
        assert restored.overview == "test"


# ── DynamicTopicQueue 测试 ──

class TestDynamicTopicQueue:
    def test_add_block(self):
        queue = DynamicTopicQueue(research_id="test")
        block = queue.add_block("Topic A", "Overview A")
        assert block.block_id == "block_1"
        assert len(queue.blocks) == 1

    def test_has_topic_case_insensitive(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("AI Safety", "")
        assert queue.has_topic("ai safety") is True
        assert queue.has_topic("AI SAFETY") is True
        assert queue.has_topic("AI Ethics") is False

    def test_has_topic_empty(self):
        queue = DynamicTopicQueue(research_id="test")
        assert queue.has_topic("") is False

    def test_max_length(self):
        queue = DynamicTopicQueue(research_id="test", max_length=2)
        queue.add_block("A", "")
        queue.add_block("B", "")
        with pytest.raises(RuntimeError):
            queue.add_block("C", "")

    def test_get_pending_block_fifo(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        queue.add_block("B", "")
        queue.mark_researching("block_1")
        pending = queue.get_pending_block()
        assert pending.block_id == "block_2"

    def test_get_pending_block_none(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        queue.mark_completed("block_1")
        assert queue.get_pending_block() is None

    def test_state_transitions(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        assert queue.mark_researching("block_1") is True
        assert queue.blocks[0].status == TopicStatus.RESEARCHING
        assert queue.mark_completed("block_1") is True
        assert queue.blocks[0].status == TopicStatus.COMPLETED

    def test_mark_failed(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        assert queue.mark_failed("block_1") is True
        assert queue.blocks[0].status == TopicStatus.FAILED

    def test_mark_nonexistent(self):
        queue = DynamicTopicQueue(research_id="test")
        assert queue.mark_researching("block_999") is False

    def test_is_all_completed(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        queue.add_block("B", "")
        assert queue.is_all_completed() is False
        queue.mark_completed("block_1")
        queue.mark_completed("block_2")
        assert queue.is_all_completed() is True

    def test_is_all_completed_with_failed(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        queue.mark_failed("block_1")
        assert queue.is_all_completed() is True

    def test_empty_is_not_all_completed(self):
        queue = DynamicTopicQueue(research_id="test")
        assert queue.is_all_completed() is False

    def test_serialization(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "overview A")
        queue.mark_completed("block_1")
        data = queue.to_dict()
        restored = DynamicTopicQueue.from_dict(data)
        assert len(restored.blocks) == 1
        assert restored.blocks[0].status == TopicStatus.COMPLETED
        assert restored.research_id == "test"
        assert restored.block_counter == 1

    def test_get_statistics(self):
        queue = DynamicTopicQueue(research_id="test")
        queue.add_block("A", "")
        queue.add_block("B", "")
        queue.mark_completed("block_1")
        queue.mark_failed("block_2")
        stats = queue.get_statistics()
        assert stats["total_blocks"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
