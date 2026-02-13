"""
75.04 多轮迭代搜索 — MultiRoundSearcher

搜索 → LLM 检测空白 → 生成细化查询 → 再搜索，
直到无空白或达到最大次数。结果累积 + URL 去重。
"""
import logging
from typing import Dict, List, Optional

from services.blog_generator.services.knowledge_gap_detector import (
    KnowledgeGapDetector,
    MAX_SEARCH_ROUNDS,
)

logger = logging.getLogger(__name__)


class MultiRoundSearcher:
    """多轮迭代搜索器"""

    def __init__(
        self,
        search_service=None,
        gap_detector: KnowledgeGapDetector = None,
        deep_scraper=None,
    ):
        self.search_service = search_service
        self.gap_detector = gap_detector
        self.deep_scraper = deep_scraper

    def search(
        self,
        topic: str,
        article_type: str = "medium",
        outline: Optional[Dict] = None,
    ) -> Dict:
        """多轮迭代搜索

        Args:
            topic: 搜索主题
            article_type: 文章类型（short/medium/long）
            outline: 大纲（可选）

        Returns:
            {
                "results": [...],      # 累积的搜索结果（已去重）
                "rounds": int,         # 实际搜索轮数
                "gaps_found": [...],   # 发现的所有知识空白
                "round_logs": [...],   # 每轮搜索日志
            }
        """
        max_rounds = MAX_SEARCH_ROUNDS.get(article_type, 5)
        accumulated: List[Dict] = []
        seen_urls = set()
        all_gaps: List[Dict] = []
        round_logs: List[Dict] = []
        current_query = topic

        for round_num in range(1, max_rounds + 1):
            # 执行搜索
            search_result = self.search_service.search(current_query)
            new_results = search_result.get("results", [])

            if not search_result.get("success") and round_num == 1:
                round_logs.append({
                    "round": round_num,
                    "query": current_query,
                    "results_count": 0,
                    "new_count": 0,
                })
                break

            # URL 去重 + 累积
            new_count = 0
            for r in new_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    accumulated.append(r)
                    new_count += 1

            round_logs.append({
                "round": round_num,
                "query": current_query,
                "results_count": len(new_results),
                "new_count": new_count,
            })

            logger.info(
                f"搜索第 {round_num}/{max_rounds} 轮: "
                f"query='{current_query}', 新增 {new_count} 条"
            )

            # 检测知识空白
            if not self.gap_detector:
                break

            gaps = self.gap_detector.detect(accumulated, topic, outline)

            if not self.gap_detector.should_continue(gaps, round_num, max_rounds):
                break

            # 记录空白并准备下一轮查询
            all_gaps.extend(gaps)
            current_query = gaps[0]["refined_query"] if gaps else topic

        return {
            "results": accumulated,
            "rounds": len(round_logs),
            "gaps_found": all_gaps,
            "round_logs": round_logs,
        }
