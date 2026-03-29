"""
41.01 深度研究框架 — 多轮迭代研究模式

灵感来源：GPT-Researcher 的 deep research 模式。
在普通搜索基础上增加：
1. 初始搜索后，LLM 分析知识缺口
2. 针对缺口生成补充搜索查询
3. 迭代搜索直到知识覆盖充分或达到最大轮数
4. 最终合并所有搜索结果

环境变量：
- DEEP_RESEARCH_ENABLED: 是否启用（默认 false）
- DEEP_RESEARCH_MAX_ROUNDS: 最大迭代轮数（默认 3）
- DEEP_RESEARCH_GAP_THRESHOLD: 缺口数量阈值，低于此值停止（默认 2）
"""
import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DeepResearchEngine:
    """多轮迭代深度研究引擎"""

    def __init__(self, llm_client, search_service):
        self.llm = llm_client
        self.search_service = search_service
        self.max_rounds = int(os.environ.get('DEEP_RESEARCH_MAX_ROUNDS', '3'))
        self.gap_threshold = int(os.environ.get('DEEP_RESEARCH_GAP_THRESHOLD', '2'))

    def _analyze_gaps(self, topic: str, current_knowledge: str,
                      search_results: List[Dict]) -> List[Dict]:
        """分析当前知识的缺口"""
        sources_summary = "\n".join(
            f"- {r.get('title', '')}: {(r.get('content', '') or r.get('snippet', ''))[:200]}"
            for r in search_results[:10]
        )

        prompt = f"""分析以下关于「{topic}」的研究素材，找出知识缺口。

已有知识摘要:
{current_knowledge[:1000] if current_knowledge else '暂无'}

已搜索到的素材:
{sources_summary}

请输出 JSON 对象，包含:
- gaps: 知识缺口数组，每个元素包含:
  - topic: 缺口主题
  - reason: 为什么这是一个缺口
  - search_query: 建议的补充搜索查询
- coverage_score: 当前知识覆盖度评分（0-100）

只输出 JSON，不要其他内容。"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            text = response.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            result = json.loads(text)
            return result.get('gaps', []), result.get('coverage_score', 50)
        except Exception as e:
            logger.warning(f"[DeepResearch] 缺口分析失败: {e}")
            return [], 80

    def run(self, topic: str, target_audience: str = "",
            initial_results: List[Dict] = None) -> Dict[str, Any]:
        """
        执行深度研究。

        Args:
            topic: 研究主题
            target_audience: 目标受众
            initial_results: 初始搜索结果（可选，避免重复搜索）

        Returns:
            {'results': List[Dict], 'rounds': int, 'total_queries': int,
             'coverage_score': int, 'gaps_found': int}
        """
        all_results = list(initial_results or [])
        seen_urls = {r.get('url', '') for r in all_results if r.get('url')}
        current_knowledge = ""
        total_queries = 0

        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"[DeepResearch] 第 {round_num}/{self.max_rounds} 轮")

            # 分析缺口
            gaps, coverage = self._analyze_gaps(topic, current_knowledge, all_results)
            logger.info(
                f"[DeepResearch] 覆盖度: {coverage}%, 缺口: {len(gaps)} 个"
            )

            # 停止条件
            if len(gaps) < self.gap_threshold:
                logger.info(f"[DeepResearch] 缺口数 < {self.gap_threshold}，停止迭代")
                break
            if coverage >= 85:
                logger.info("[DeepResearch] 覆盖度 >= 85%，停止迭代")
                break

            # 补充搜索
            for gap in gaps[:3]:  # 每轮最多补充 3 个查询
                query = gap.get('search_query', gap.get('topic', ''))
                if not query:
                    continue
                total_queries += 1
                try:
                    result = self.search_service.search(query, max_results=5)
                    if result.get('success') and result.get('results'):
                        for r in result['results']:
                            url = r.get('url', '')
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                all_results.append(r)
                except Exception as e:
                    logger.warning(f"[DeepResearch] 补充搜索失败 [{query}]: {e}")

            # 更新知识摘要
            current_knowledge = "\n".join(
                (r.get('content', '') or r.get('snippet', ''))[:300]
                for r in all_results[:15]
            )

        return {
            'results': all_results,
            'rounds': round_num if 'round_num' in dir() else 1,
            'total_queries': total_queries,
            'coverage_score': coverage if 'coverage' in dir() else 0,
            'gaps_found': len(gaps) if 'gaps' in dir() else 0,
        }
