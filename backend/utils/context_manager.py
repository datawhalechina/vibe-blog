"""
统一上下文压缩管理器 — 融合消息级摘要 + 多维度触发 + 现有三层压缩

编排四层压缩管道：
  Layer 1: SemanticCompressor — embedding 语义筛选（快速，低成本）
  Layer 2: ContextCompressor — 消息级工具结果省略 + 内容截断
  Layer 3: LLM 摘要压缩（可选，默认关闭）
  Layer 4: ContextGuard — 兜底 prompt 裁剪

触发条件支持四种模式（OR 逻辑）：
  tokens   — token 总数达到阈值
  messages — 消息条数达到阈值
  fraction — token 使用率达到模型上下文窗口百分比
  ratio    — 与现有 usage_ratio 兼容

环境变量:
  CONTEXT_COMPRESSION_ENABLED: 总开关 (default: true)
  SUMMARIZATION_ENABLED: LLM 摘要层开关 (default: false)
  SUMMARIZATION_MODEL: 摘要模型名称 (default: None, 使用默认模型)
  SEMANTIC_COMPRESS_ENABLED: 语义压缩开关 (default: false)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from utils.context_guard import ContextGuard, estimate_tokens
from utils.context_compressor import ContextCompressor

logger = logging.getLogger(__name__)

TriggerType = Literal["tokens", "messages", "fraction", "ratio"]
KeepType = Literal["messages", "tokens", "fraction"]


@dataclass
class CompressionTrigger:
    """压缩触发条件 — 支持 tokens/messages/fraction/ratio 四种模式"""
    type: TriggerType
    value: float

    def is_met(
        self,
        token_count: int,
        message_count: int,
        context_limit: int,
        usage_ratio: float,
    ) -> bool:
        """检查触发条件是否满足"""
        if self.type == "tokens":
            return token_count >= self.value
        elif self.type == "messages":
            return message_count >= self.value
        elif self.type == "fraction":
            return token_count >= context_limit * self.value
        elif self.type == "ratio":
            return usage_ratio >= self.value
        return False


@dataclass
class CompressionConfig:
    """压缩配置 — 融合多维度触发 + 保留策略 + 各层开关"""
    enabled: bool = True
    triggers: List[CompressionTrigger] = field(default_factory=lambda: [
        CompressionTrigger(type="ratio", value=0.70),
    ])
    keep_type: KeepType = "messages"
    keep_value: int = 10
    summarization_enabled: bool = False
    summarization_model: Optional[str] = None
    semantic_enabled: bool = False

    @classmethod
    def from_env(cls) -> "CompressionConfig":
        """从环境变量构建配置"""
        return cls(
            enabled=os.getenv("CONTEXT_COMPRESSION_ENABLED", "true").lower() == "true",
            summarization_enabled=os.getenv("SUMMARIZATION_ENABLED", "false").lower() == "true",
            summarization_model=os.getenv("SUMMARIZATION_MODEL") or None,
            semantic_enabled=os.getenv("SEMANTIC_COMPRESS_ENABLED", "false").lower() == "true",
        )


class ContextManager:
    """
    统一上下文压缩管理器 — 编排四层压缩管道。

    用法:
        config = CompressionConfig.from_env()
        manager = ContextManager(config=config, model_name="gpt-4o")
        result = manager.compress(messages=messages, search_results=results, query="topic")
    """

    def __init__(
        self,
        config: Optional[CompressionConfig] = None,
        model_name: str = "gpt-4o",
        compressor: Optional[ContextCompressor] = None,
        semantic_compressor=None,
        llm_service=None,
    ):
        self.config = config or CompressionConfig.from_env()
        self.model_name = model_name
        self.guard = ContextGuard(model_name)
        self.compressor = compressor or ContextCompressor(model_name=model_name)
        self.semantic_compressor = semantic_compressor
        self.llm = llm_service

    def _compute_metrics(self, messages: List[Dict]) -> Dict[str, Any]:
        """计算当前上下文指标：token 数、消息数、usage_ratio"""
        total_text = ""
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_text += content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total_text += block.get("text", "")
        token_count = estimate_tokens(total_text)
        context_limit = self.guard.context_limit
        safe_limit = self.guard.safe_input_limit
        usage_ratio = token_count / safe_limit if safe_limit > 0 else 0.0
        return {
            "token_count": token_count,
            "message_count": len(messages),
            "context_limit": context_limit,
            "usage_ratio": usage_ratio,
        }

    def _should_compress(self, metrics: Dict[str, Any]) -> bool:
        """检查是否有任一触发条件满足（OR 逻辑）"""
        return any(
            t.is_met(
                token_count=metrics["token_count"],
                message_count=metrics["message_count"],
                context_limit=metrics["context_limit"],
                usage_ratio=metrics["usage_ratio"],
            )
            for t in self.config.triggers
        )

    def compress(
        self,
        messages: List[Dict],
        search_results: List[Dict],
        query: str = "",
        node_name: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        执行统一压缩管道。

        Returns:
            压缩结果 dict（含 _messages / search_results / _compression_layer 等），
            无需压缩时返回 None。
        """
        if not self.config.enabled:
            return None

        metrics = self._compute_metrics(messages)

        if not self._should_compress(metrics):
            return None

        patch: Dict[str, Any] = {
            "_compression_triggered": True,
            "_pre_compression_tokens": metrics["token_count"],
        }
        usage_ratio = metrics["usage_ratio"]

        # Layer 1: 语义压缩（搜索结果）
        if self.config.semantic_enabled and self.semantic_compressor and search_results:
            try:
                compressed_results = self.semantic_compressor.compress(
                    query, search_results
                )
                if len(compressed_results) < len(search_results):
                    patch["search_results"] = compressed_results
                    patch["_compression_layer"] = 1
                    logger.info(
                        "[ContextManager L1] search_results %d -> %d",
                        len(search_results), len(compressed_results),
                    )
            except Exception as e:
                logger.warning("[ContextManager L1] semantic compress failed: %s", e)

        # Layer 2: 消息级压缩（工具结果省略 + 内容截断）
        compressed_messages = self.compressor.apply_strategy(
            list(messages), usage_ratio
        )
        if compressed_messages is not messages:
            patch["_messages"] = compressed_messages
            patch.setdefault("_compression_layer", 2)

        return patch
