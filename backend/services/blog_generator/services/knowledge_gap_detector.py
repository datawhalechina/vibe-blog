"""
75.04 知识空白检测 — KnowledgeGapDetector

使用 LLM 检测搜索结果中的知识空白，为每个空白点生成细化搜索查询。
"""
import json
import logging
from typing import Dict, List, Optional

from ..schemas.outputs import DetectedKnowledgeGapsOutput
from ..structured_output import parse_structured_output, repair_legacy_json

logger = logging.getLogger(__name__)

# 按文章类型的最大搜索轮数
MAX_SEARCH_ROUNDS = {
    "mini": 2,
    "short": 3,
    "medium": 5,
    "long": 8,
}

GAP_DETECTION_PROMPT = """分析以下搜索结果，检测关于「{topic}」的知识空白。

搜索结果摘要：
{results_summary}

{outline_section}

请找出搜索结果中缺少的关键信息，包括：
- 缺少的概念解释
- 缺少的数据支撑
- 缺少的实例说明

输出 JSON 数组，每个元素包含：
- "gap": 空白描述
- "refined_query": 用于补充搜索的细化查询

如果没有明显空白，返回空数组 []。
只输出 JSON，不要其他文字。"""


class KnowledgeGapDetector:
    """知识空白检测器"""

    def __init__(self, llm_service=None):
        self.llm_service = llm_service

    def detect(
        self,
        search_results: List[Dict],
        topic: str,
        outline: Optional[Dict] = None,
    ) -> List[Dict]:
        """检测知识空白

        Args:
            search_results: 搜索结果列表
            topic: 主题
            outline: 大纲（可选）

        Returns:
            空白列表 [{"gap": "...", "refined_query": "..."}]
        """
        if not self.llm_service:
            return []

        # 构建搜索结果摘要
        summaries = []
        for r in search_results[:10]:
            title = r.get("title", "")
            snippet = r.get("snippet", r.get("content", ""))[:200]
            summaries.append(f"- {title}: {snippet}")
        results_summary = "\n".join(summaries) if summaries else "（无搜索结果）"

        outline_section = ""
        if outline:
            outline_section = f"文章大纲：\n{json.dumps(outline, ensure_ascii=False, indent=2)[:2000]}"

        prompt = GAP_DETECTION_PROMPT.format(
            topic=topic,
            results_summary=results_summary,
            outline_section=outline_section,
        )

        try:
            response = self.llm_service.chat(
                [{"role": "user", "content": prompt}],
                caller="knowledge_gap_detector",
            )
            if not response:
                return []
            return parse_structured_output(
                DetectedKnowledgeGapsOutput,
                response,
                mode="compat",
                repair=repair_legacy_json,
            ).model_dump(mode="json")
        except Exception as e:
            logger.warning(f"知识空白检测失败: {e}")
            return []

    @staticmethod
    def should_continue(gaps: List[Dict], current_round: int, max_rounds: int) -> bool:
        """判断是否继续搜索"""
        if not gaps:
            return False
        return current_round < max_rounds
