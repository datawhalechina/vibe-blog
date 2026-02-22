"""
1003.04 动态主题队列 DynamicTopicQueue

迁移自 DeepTutor data_structures.py，适配 vibe-blog LangGraph 架构。
提供主题块级调度、状态机流转、去重、容量控制、序列化。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class TopicStatus(Enum):
    """主题块状态"""
    PENDING = "pending"
    RESEARCHING = "researching"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TopicBlock:
    """主题块 — 队列的最小调度单元"""
    block_id: str
    sub_topic: str
    overview: str
    status: TopicStatus = TopicStatus.PENDING
    search_traces: list = field(default_factory=list)
    iteration_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def add_search_trace(self, trace: dict) -> None:
        """添加搜索追踪记录"""
        self.search_traces.append(trace)
        self.updated_at = datetime.now().isoformat()

    def get_all_summaries(self) -> str:
        """拼接所有追踪的摘要"""
        if not self.search_traces:
            return ""
        return "\n".join(
            f"[{t.get('query', '')}] {t.get('summary', '')}"
            for t in self.search_traces
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TopicBlock":
        data_copy = data.copy()
        if isinstance(data_copy.get("status"), str):
            data_copy["status"] = TopicStatus(data_copy["status"])
        return cls(**data_copy)


class DynamicTopicQueue:
    """
    动态主题队列 — 主题块级调度中心

    核心能力：
    - add_block(): 运行时追加主题块（支持容量限制）
    - has_topic(): 大小写不敏感去重
    - get_pending_block(): FIFO 获取下一个待处理块
    - 状态流转: PENDING → RESEARCHING → COMPLETED/FAILED
    - to_dict/from_dict: 序列化（由 SharedState checkpoint 管理持久化）
    """

    def __init__(self, research_id: str, max_length: Optional[int] = None):
        self.research_id = research_id
        self.blocks: List[TopicBlock] = []
        self.block_counter = 0
        self.created_at = datetime.now().isoformat()
        self.max_length = max_length if isinstance(max_length, int) and max_length > 0 else None

    @staticmethod
    def _normalize_topic(text: str) -> str:
        return (text or "").strip().lower()

    def add_block(self, sub_topic: str, overview: str) -> TopicBlock:
        """添加新主题块，超过容量抛出 RuntimeError"""
        if self.max_length and len(self.blocks) >= self.max_length:
            raise RuntimeError(f"Queue capacity reached ({self.max_length})")
        self.block_counter += 1
        block = TopicBlock(
            block_id=f"block_{self.block_counter}",
            sub_topic=sub_topic,
            overview=overview,
        )
        self.blocks.append(block)
        return block

    def has_topic(self, sub_topic: str) -> bool:
        """大小写不敏感检查主题是否已存在"""
        target = self._normalize_topic(sub_topic)
        if not target:
            return False
        return any(self._normalize_topic(b.sub_topic) == target for b in self.blocks)

    def get_pending_block(self) -> Optional[TopicBlock]:
        """FIFO 获取下一个 PENDING 状态的块"""
        for block in self.blocks:
            if block.status == TopicStatus.PENDING:
                return block
        return None

    def _find_block(self, block_id: str) -> Optional[TopicBlock]:
        for block in self.blocks:
            if block.block_id == block_id:
                return block
        return None

    def mark_researching(self, block_id: str) -> bool:
        block = self._find_block(block_id)
        if not block:
            return False
        block.status = TopicStatus.RESEARCHING
        block.updated_at = datetime.now().isoformat()
        return True

    def mark_completed(self, block_id: str) -> bool:
        block = self._find_block(block_id)
        if not block:
            return False
        block.status = TopicStatus.COMPLETED
        block.updated_at = datetime.now().isoformat()
        return True

    def mark_failed(self, block_id: str) -> bool:
        block = self._find_block(block_id)
        if not block:
            return False
        block.status = TopicStatus.FAILED
        block.updated_at = datetime.now().isoformat()
        return True

    def is_all_completed(self) -> bool:
        """所有块都完成（COMPLETED 或 FAILED）时返回 True，空队列返回 False"""
        if not self.blocks:
            return False
        return all(
            b.status in (TopicStatus.COMPLETED, TopicStatus.FAILED)
            for b in self.blocks
        )

    def get_statistics(self) -> Dict[str, int]:
        stats = {"total_blocks": len(self.blocks), "pending": 0,
                 "researching": 0, "completed": 0, "failed": 0}
        for b in self.blocks:
            stats[b.status.value] = stats.get(b.status.value, 0) + 1
        return stats

    def to_dict(self) -> dict:
        return {
            "research_id": self.research_id,
            "blocks": [b.to_dict() for b in self.blocks],
            "block_counter": self.block_counter,
            "created_at": self.created_at,
            "max_length": self.max_length,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DynamicTopicQueue":
        queue = cls(
            research_id=data.get("research_id", ""),
            max_length=data.get("max_length"),
        )
        queue.block_counter = data.get("block_counter", 0)
        queue.created_at = data.get("created_at", "")
        queue.blocks = [TopicBlock.from_dict(b) for b in data.get("blocks", [])]
        return queue
