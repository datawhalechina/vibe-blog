"""
1003.05 Analysis Loop — AnalysisInvestigator

对应 DeepTutor InvestigateAgent，在 researcher 之后、planner 之前运行。
基于初始搜索结果分析知识缺口，生成补充查询并执行搜索。
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AnalysisInvestigator:
    """分析调查器 — Analysis Loop 的核心驱动"""

    def __init__(self, llm_client, search_service=None):
        self.llm = llm_client
        self.search_service = search_service
        self.max_queries_per_round = 3

    def _build_context(self, state: Dict[str, Any],
                       knowledge_chain: List[dict]) -> str:
        """构建 LLM 上下文"""
        topic = state.get("topic", "")
        bg = state.get("background_knowledge", "") or ""
        summaries = "\n".join(
            f"- [{item.get('cite_id', '')}] {item.get('summary') or item.get('query', '')}"
            for item in knowledge_chain
        ) if knowledge_chain else "暂无"

        search_results = state.get("search_results", [])
        sources = "\n".join(
            f"- {r.get('title', '')}: {(r.get('content', '') or '')[:200]}"
            for r in search_results[:8]
        ) if search_results else "暂无"

        return (
            f"研究主题: {topic}\n\n"
            f"背景知识:\n{bg[:1000]}\n\n"
            f"已积累的知识链:\n{summaries}\n\n"
            f"已有搜索结果:\n{sources}"
        )

    def _call_llm(self, context: str) -> dict:
        """调用 LLM 判断是否继续调查"""
        prompt = f"""{context}

请分析以上研究素材，判断是否需要继续深入调查。

输出 JSON 对象:
{{
  "reasoning": "分析推理过程",
  "should_stop": true/false,
  "queries": [
    {{"query": "补充搜索查询", "tool_type": "web_search"}}
  ]
}}

如果知识已经充分，设置 should_stop=true 且 queries 为空数组。
只输出 JSON，不要其他内容。"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.warning(f"[AnalysisInvestigator] LLM 调用失败: {e}")
            return {"should_stop": True, "queries": [], "reasoning": str(e)}

    def _format_results(self, results: list) -> str:
        return "\n".join(
            f"[{r.get('title', '')}] {(r.get('content', '') or '')[:300]}"
            for r in results[:5]
        )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行一轮调查"""
        round_num = state.get("analysis_round", 0) + 1
        knowledge_chain = list(state.get("analysis_knowledge_chain", []))

        context = self._build_context(state, knowledge_chain)
        decision = self._call_llm(context)

        if decision.get("should_stop", True) or not decision.get("queries"):
            state["analysis_should_stop"] = True
            state["analysis_round"] = round_num
            state["_new_knowledge_ids"] = []
            return state

        new_items = []
        queries = decision["queries"][:self.max_queries_per_round]
        for i, q in enumerate(queries, 1):
            query_text = q.get("query", "")
            if not query_text or not self.search_service:
                continue
            try:
                result = self.search_service.search(query_text, max_results=5)
                if result.get("success") and result.get("results"):
                    item = {
                        "cite_id": f"AK-{round_num}-{i}",
                        "tool_type": q.get("tool_type", "web_search"),
                        "query": query_text,
                        "raw_result": self._format_results(result["results"]),
                        "summary": "",
                    }
                    new_items.append(item)
                    # 追加搜索结果到全局
                    for r in result["results"]:
                        state.setdefault("search_results", []).append(r)
            except Exception as e:
                logger.warning(f"[AnalysisInvestigator] 搜索失败 [{query_text}]: {e}")

        knowledge_chain.extend(new_items)
        state["analysis_knowledge_chain"] = knowledge_chain
        state["analysis_should_stop"] = False
        state["analysis_round"] = round_num
        state["_new_knowledge_ids"] = [item["cite_id"] for item in new_items]
        return state
