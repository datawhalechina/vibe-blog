"""
1003.05 Analysis Loop — AnalysisNoteAgent

对应 DeepTutor NoteAgent，对新检索到的知识生成结构化摘要。
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AnalysisNoteAgent:
    """分析笔记 Agent — 对知识链中的新项生成摘要"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """对 _new_knowledge_ids 指向的知识项生成摘要"""
        new_ids = state.get("_new_knowledge_ids", [])
        if not new_ids:
            return state

        knowledge_chain = state.get("analysis_knowledge_chain", [])
        topic = state.get("topic", "")

        for item in knowledge_chain:
            if item.get("cite_id") not in new_ids:
                continue
            if item.get("summary"):
                continue

            raw = item.get("raw_result", "")
            if not raw:
                continue

            summary = self._generate_summary(topic, item.get("query", ""), raw)
            item["summary"] = summary

        state["analysis_knowledge_chain"] = knowledge_chain

        # 合并摘要到 accumulated_knowledge
        all_summaries = "\n".join(
            f"- {item.get('summary', '')}"
            for item in knowledge_chain
            if item.get("summary")
        )
        if all_summaries:
            existing = state.get("accumulated_knowledge", "") or ""
            state["accumulated_knowledge"] = (
                existing + "\n\n[Analysis Loop 知识摘要]\n" + all_summaries
            ).strip()

        return state

    def _generate_summary(self, topic: str, query: str, raw_result: str) -> str:
        """调用 LLM 生成摘要"""
        prompt = f"""请为以下关于「{topic}」的搜索结果生成简洁摘要（2-3 句话）。

搜索查询: {query}
搜索结果:
{raw_result[:2000]}

只输出摘要文本，不要其他内容。"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            return response.strip()[:500]
        except Exception as e:
            logger.warning(f"[AnalysisNote] 摘要生成失败: {e}")
            return ""
