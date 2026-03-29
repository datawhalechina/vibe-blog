"""
41.02 源可信度筛选 — LLM 驱动的搜索结果质量评估

在 SmartSearchService 搜索结果合并去重之后，按权威性/时效性/相关性/深度
四维评分，筛选高质量结果。失败时降级返回原始结果。
"""

import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 四维权重
WEIGHTS = {
    'authority': 0.30,
    'freshness': 0.25,
    'relevance': 0.30,
    'depth': 0.15,
}

DEFAULT_MAX_RESULTS = 10
DEFAULT_MIN_SCORE = 5.0
# 搜索结果 <= 此数量时跳过评估（数据量太少，筛选意义不大）
SKIP_THRESHOLD = 5


class SourceCredibilityFilter:
    """LLM 驱动的源可信度筛选器"""

    def __init__(self, llm_client, max_results: int = None, min_score: float = None):
        self.llm = llm_client
        self.max_results = max_results or int(
            os.environ.get('SOURCE_CREDIBILITY_MAX_RESULTS', DEFAULT_MAX_RESULTS)
        )
        self.min_score = min_score or float(
            os.environ.get('SOURCE_CREDIBILITY_MIN_SCORE', DEFAULT_MIN_SCORE)
        )

    def curate(
        self,
        query: str,
        search_results: List[Dict],
        max_results: Optional[int] = None,
    ) -> List[Dict]:
        """执行 LLM 可信度评估，返回筛选后的结果列表"""
        if not search_results:
            return []

        # 短路：数据量太少时跳过评估
        if len(search_results) <= SKIP_THRESHOLD:
            logger.info(f"搜索结果仅 {len(search_results)} 条，跳过可信度评估")
            return search_results

        effective_max = max_results or self.max_results

        try:
            prompt = self._build_prompt(query, search_results, effective_max)
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                caller="source_credibility_filter",
            )
            if not response:
                logger.warning("可信度评估返回空响应，降级返回原始列表")
                return search_results

            scores = self._parse_response(response)
            if not scores:
                logger.warning("可信度评估解析失败，降级返回原始列表")
                return search_results

            # 按 total_score 降序排列，过滤低分，截断
            filtered = []
            for item in scores:
                idx = item.get('index', 0) - 1  # 1-based → 0-based
                if 0 <= idx < len(search_results) and item.get('total_score', 0) >= self.min_score:
                    result = search_results[idx].copy()
                    result['credibility_score'] = item.get('total_score', 0)
                    result['credibility_detail'] = {
                        'authority': item.get('authority', 0),
                        'freshness': item.get('freshness', 0),
                        'relevance': item.get('relevance', 0),
                        'depth': item.get('depth', 0),
                        'reason': item.get('reason', ''),
                    }
                    filtered.append(result)

            filtered.sort(key=lambda x: x.get('credibility_score', 0), reverse=True)
            result = filtered[:effective_max]
            logger.info(f"可信度筛选: {len(search_results)} → {len(result)} 条")
            return result

        except Exception as e:
            logger.error(f"源可信度筛选失败: {e}，降级返回原始结果")
            return search_results

    def _build_prompt(self, query: str, results: List[Dict], max_results: int) -> str:
        """构建评估 Prompt"""
        items = []
        for i, r in enumerate(results, 1):
            content_preview = (r.get('content', '') or '')[:500]
            items.append(
                f"[{i}] 标题: {r.get('title', '无标题')}\n"
                f"URL: {r.get('url', '')}\n"
                f"来源: {r.get('source', '未知')}\n"
                f"发布日期: {r.get('publish_date', '未知')}\n"
                f"内容摘要: {content_preview}"
            )
        sources_text = "\n---\n".join(items)

        return (
            f"你是一位专业的信息源质量评估专家。请对以下搜索结果进行可信度评估。\n\n"
            f"研究主题：{query}\n\n"
            f"搜索结果（共 {len(results)} 条）：\n{sources_text}\n\n"
            f"请按以下四个维度对每条结果评分（1-10 分）：\n"
            f"1. authority: 来源是否为官方机构、知名技术博客、学术期刊\n"
            f"2. freshness: 内容是否为近期发布（2024年以后优先）\n"
            f"3. relevance: 与研究主题\"{query}\"的匹配程度\n"
            f"4. depth: 是否包含深度分析、数据统计、代码示例、案例研究\n\n"
            f"返回 JSON 数组，按综合得分降序排列，最多保留 {max_results} 条：\n"
            f'[{{"index":1,"authority":8,"freshness":9,"relevance":10,"depth":7,'
            f'"total_score":8.6,"reason":"一句话评估理由"}}]\n\n'
            f"total_score 加权公式：authority*0.30 + freshness*0.25 + relevance*0.30 + depth*0.15\n"
            f"仅返回 JSON 数组，不要包含 markdown 代码块或其他文本。"
        )

    @staticmethod
    def _parse_response(response: str) -> List[Dict]:
        """解析 LLM 响应为评分列表"""
        text = response.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()

        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and 'results' in parsed:
            return parsed['results']
        return []
