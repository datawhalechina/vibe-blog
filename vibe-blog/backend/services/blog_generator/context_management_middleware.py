"""
三层上下文管理中间件 -- AgentFold + ReSum 融合

将 LLM 主动压缩 (AgentFold) 和周期性摘要 (ReSum) 融合为三层策略，
通过 MiddlewarePipeline 在节点执行前自动调度：

  Layer 1 (fold ~ summary): SemanticCompressor embedding 筛选 (快速, 低成本)
  Layer 2 (>= summary):     LLM 主动压缩 (AgentFold 式, 精准, 中成本)
  Layer 3 (>= summary):     全量摘要替换 (ReSum 式, 兜底, 高成本)

环境变量:
  CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED: 总开关 (default: false)
  CONTEXT_FOLD_THRESHOLD:    Layer 1 触发阈值 (default: 0.7)
  CONTEXT_SUMMARY_THRESHOLD: Layer 2/3 触发阈值 (default: 0.9)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from utils.context_guard import ContextGuard, estimate_tokens

logger = logging.getLogger(__name__)

# 阈值配置
FOLD_THRESHOLD = float(os.environ.get("CONTEXT_FOLD_THRESHOLD", "0.7"))
SUMMARY_THRESHOLD = float(os.environ.get("CONTEXT_SUMMARY_THRESHOLD", "0.9"))


class ContextManagementMiddleware:
    """
    三层上下文管理中间件 -- 融合 AgentFold + ReSum + 现有压缩策略。

    满足 NodeMiddleware 协议 (before_node / after_node)。
    """

    def __init__(
        self,
        llm_service=None,
        semantic_compressor=None,
        context_guard: Optional[ContextGuard] = None,
        model_name: str = "gpt-4o",
    ):
        self.llm = llm_service
        self.semantic_compressor = semantic_compressor
        self.guard = context_guard or ContextGuard(model_name)
        self._last_summary: Optional[str] = None
        self._compression_count = 0

    # ---- NodeMiddleware protocol ----

    def before_node(
        self, state: Dict[str, Any], node_name: str
    ) -> Optional[Dict[str, Any]]:
        if os.getenv("CONTEXT_COMPRESSION_MIDDLEWARE_ENABLED", "false").lower() != "true":
            return None

        usage = self._estimate_usage(state)
        if usage < FOLD_THRESHOLD:
            return None

        patch: Dict[str, Any] = {"_context_usage_ratio": usage}

        if usage < SUMMARY_THRESHOLD:
            # Layer 1: SemanticCompressor
            layer_patch = self._apply_layer1(state, node_name)
        else:
            # >= summary_threshold: Layer 3 if multiple context parts, else Layer 2
            has_extra_context = bool(
                state.get("distilled_sources") or state.get("review_history")
            )
            if has_extra_context:
                layer_patch = self._apply_layer3(state, node_name)
            else:
                layer_patch = self._apply_layer2(state, node_name)

        patch.update(layer_patch)
        return patch if len(patch) > 1 else None

    def after_node(
        self, state: Dict[str, Any], node_name: str
    ) -> Optional[Dict[str, Any]]:
        return None

    # ---- Usage estimation ----

    def _estimate_usage(self, state: Dict[str, Any]) -> float:
        total_text = ""
        for key in ("research_data", "sections", "outline",
                     "review_history", "search_results", "distilled_sources"):
            val = state.get(key)
            if val:
                total_text += str(val)
        tokens = estimate_tokens(total_text)
        limit = self.guard.safe_input_limit
        return tokens / limit if limit > 0 else 0.0

    def _apply_layer1(
        self, state: Dict[str, Any], node_name: str
    ) -> Dict[str, Any]:
        """Layer 1: embedding-based semantic filtering of search results."""
        if not self.semantic_compressor:
            return {}
        search_results = state.get("search_results", [])
        topic = state.get("topic", "")
        if search_results and topic:
            compressed = self.semantic_compressor.compress(topic, search_results)
            logger.info(
                "[ContextMgmt L1] %s: search_results %d -> %d",
                node_name, len(search_results), len(compressed),
            )
            return {"search_results": compressed, "_context_layer": 1}
        return {}

    def _apply_layer2(
        self, state: Dict[str, Any], node_name: str
    ) -> Dict[str, Any]:
        """Layer 2: LLM active compression (AgentFold style)."""
        if not self.llm:
            return self._apply_layer1(state, node_name)

        research_data = state.get("research_data", "")
        if not research_data or len(str(research_data)) < 1000:
            return self._apply_layer1(state, node_name)

        try:
            compressed = self._llm_compress(str(research_data), state.get("topic", ""))
            self._compression_count += 1
            logger.info(
                "[ContextMgmt L2] %s: research_data %d -> %d chars (compression #%d)",
                node_name, len(str(research_data)), len(compressed),
                self._compression_count,
            )
            return {"research_data": compressed, "_context_layer": 2}
        except Exception as e:
            logger.warning("[ContextMgmt L2] compression failed, degrade to L1: %s", e)
            return self._apply_layer1(state, node_name)

    def _apply_layer3(
        self, state: Dict[str, Any], node_name: str
    ) -> Dict[str, Any]:
        """Layer 3: ReSum full summary -- replace entire context."""
        if not self.llm:
            return self._apply_layer2(state, node_name)

        context_parts = []
        for key in ("research_data", "distilled_sources", "review_history"):
            val = state.get(key)
            if val:
                context_parts.append(f"[{key}]: {str(val)[:3000]}")

        if not context_parts:
            return self._apply_layer2(state, node_name)

        try:
            summary = self._resum_summarize(
                "\n\n".join(context_parts), state.get("topic", ""),
            )
            self._last_summary = summary
            logger.info(
                "[ContextMgmt L3] %s: full summary done (%d chars)",
                node_name, len(summary),
            )
            return {
                "research_data": summary,
                "distilled_sources": [],
                "_context_layer": 3,
                "_context_summary": summary,
            }
        except Exception as e:
            logger.warning("[ContextMgmt L3] summary failed, degrade to L2: %s", e)
            return self._apply_layer2(state, node_name)

    def _llm_compress(self, content: str, topic: str) -> str:
        """AgentFold-style LLM compression."""
        prompt = (
            f"你是一个上下文压缩专家。以下是关于「{topic}」的研究资料。\n"
            f"请保留与主题直接相关的关键事实、数据和论据，"
            f"删除重复信息、无关细节和过渡性文字。\n"
            f"输出压缩后的精华内容，保持信息完整性。\n\n"
            f"原始内容：\n{content[:8000]}"
        )
        return self.llm.chat(messages=[{"role": "user", "content": prompt}])

    def _resum_summarize(self, context: str, topic: str) -> str:
        """ReSum-style full summary."""
        if self._last_summary:
            prompt = RESUM_INCREMENTAL_PROMPT.format(
                topic=topic, last_summary=self._last_summary, context=context[:6000],
            )
        else:
            prompt = RESUM_INITIAL_PROMPT.format(topic=topic, context=context[:8000])
        return self.llm.chat(messages=[{"role": "user", "content": prompt}])


# ---- Prompt templates (migrated from ReSum) ----

RESUM_INITIAL_PROMPT = """你是一个信息提取专家。请分析以下关于「{topic}」的研究上下文，提取关键信息。

任务要求：
1. 提取与主题直接相关的关键事实、数据和论据
2. 保留所有引用来源（URL、作者、日期）
3. 去除重复信息和无关细节
4. 输出结构化摘要

研究上下文：
{context}

请输出精炼的摘要："""

RESUM_INCREMENTAL_PROMPT = """你是一个信息提取专家。以下是关于「{topic}」的上次摘要和新增研究上下文。

任务要求：
1. 以上次摘要为基线，整合新增信息
2. 识别新增的关键发现和数据
3. 保留所有引用来源
4. 输出更新后的完整摘要

上次摘要：
{last_summary}

新增上下文：
{context}

请输出更新后的摘要："""
