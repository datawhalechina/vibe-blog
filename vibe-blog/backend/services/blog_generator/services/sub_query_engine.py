"""
41.04 子查询并行研究引擎

迁移自 GPT-Researcher 的 plan_research + asyncio.gather 模式。
LLM 生成 N 个语义互补的子查询 → ThreadPoolExecutor 并行搜索 → 合并去重。
三级降级：LLM+context → LLM → 硬编码模板。
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

DEFAULT_SUB_QUERY_COUNT = 4
MAX_SUB_QUERY_COUNT = 8
MIN_SUB_QUERY_COUNT = 2


class SubQueryEngine:
    """子查询并行研究引擎"""

    def __init__(self, llm_client, search_service, prompt_manager=None):
        self.llm = llm_client
        self.search_service = search_service
        self.prompt_manager = prompt_manager

        self.sub_query_count = self._get_config_int(
            'SUB_QUERY_COUNT', DEFAULT_SUB_QUERY_COUNT,
            min_val=MIN_SUB_QUERY_COUNT, max_val=MAX_SUB_QUERY_COUNT,
        )
        self.context_enabled = os.environ.get(
            'SUB_QUERY_CONTEXT_ENABLED', 'true'
        ).lower() == 'true'
        self.max_workers = self._get_config_int(
            'SUB_QUERY_MAX_WORKERS', 4, min_val=1, max_val=8,
        )
        self.include_original = os.environ.get(
            'SUB_QUERY_INCLUDE_ORIGINAL', 'true'
        ).lower() == 'true'

    @staticmethod
    def _get_config_int(key: str, default: int,
                        min_val: int = 0, max_val: int = 100) -> int:
        try:
            val = int(os.environ.get(key, str(default)))
            return max(min_val, min(max_val, val))
        except (ValueError, TypeError):
            return default

    # ── 子查询生成 ──────────────────────────────

    def generate_sub_queries(
        self, topic: str, target_audience: str = '', context: str = '',
    ) -> List[str]:
        """LLM 生成 N 个语义互补的子查询（三级降级）"""
        # Level 1: LLM + context
        if self.llm:
            try:
                queries = self._llm_generate(topic, target_audience, context)
                if queries and len(queries) >= 2:
                    logger.info(f"子查询生成成功 (LLM+context): {queries}")
                    return queries[:self.sub_query_count]
            except Exception as e:
                logger.warning(f"LLM 子查询生成失败 (Level 1): {e}")

        # Level 2: LLM 无 context
        if self.llm:
            try:
                queries = self._llm_generate(topic, target_audience, context='')
                if queries and len(queries) >= 2:
                    logger.info(f"子查询生成成功 (LLM): {queries}")
                    return queries[:self.sub_query_count]
            except Exception as e:
                logger.warning(f"LLM 子查询生成失败 (Level 2): {e}")

        # Level 3: 硬编码模板
        logger.warning("LLM 不可用，使用硬编码子查询模板")
        return self._hardcoded_queries(topic)

    def _llm_generate(self, topic: str, target_audience: str, context: str) -> List[str]:
        prompt = self._build_sub_query_prompt(topic, target_audience, context)
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            caller="sub_query_engine",
        )
        return self._parse_queries_response(response)

    def _build_sub_query_prompt(self, topic: str, target_audience: str, context: str) -> str:
        if self.prompt_manager and hasattr(self.prompt_manager, 'render_sub_query_generation'):
            return self.prompt_manager.render_sub_query_generation(
                topic=topic, target_audience=target_audience,
                context=context, count=self.sub_query_count,
            )

        context_block = ""
        if context:
            context_block = (
                f"\n以下是关于该主题的初始搜索结果，请基于这些信息"
                f"生成更精准的子查询:\n{context[:2000]}\n"
            )

        examples = ", ".join([f'"查询{i+1}"' for i in range(self.sub_query_count)])

        return (
            f"你是一位资深研究助手。请为以下博客主题生成 {self.sub_query_count} 个搜索查询，\n"
            f"这些查询应从不同角度覆盖该主题，帮助收集全面的写作素材。\n\n"
            f"主题: \"{topic}\"\n"
            f"目标受众: {target_audience or '技术开发者'}\n"
            f"{context_block}\n"
            f"要求:\n"
            f"1. 每个查询应覆盖主题的不同方面（如: 核心概念、实践案例、对比分析、最新动态）\n"
            f"2. 查询应具体且可搜索，避免过于宽泛\n"
            f"3. 混合使用中英文查询以获得更广泛的结果\n"
            f"4. 返回 JSON 数组格式: [{examples}]\n\n"
            f"请直接返回 JSON 数组，不要包含其他内容。"
        )

    @staticmethod
    def _parse_queries_response(response: str) -> List[str]:
        text = response.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()
        result = json.loads(text)
        if isinstance(result, list):
            return [q for q in result if isinstance(q, str) and q.strip()]
        if isinstance(result, dict) and 'queries' in result:
            return [q for q in result['queries'] if isinstance(q, str) and q.strip()]
        return []

    @staticmethod
    def _hardcoded_queries(topic: str) -> List[str]:
        from datetime import datetime
        year = datetime.now().year
        return [
            f"{topic} 核心概念 tutorial",
            f"{topic} 最佳实践 best practices",
            f"{topic} 实际案例 use cases",
            f"{topic} 最新进展 {year - 1} {year}",
        ]

    # ── 并行搜索 ──────────────────────────────

    def parallel_search(
        self, sub_queries: List[str], original_topic: str = '',
        max_results_per_query: int = 5,
    ) -> List[Dict[str, Any]]:
        """并行执行所有子查询的搜索，委托 SmartSearchService"""
        queries = list(sub_queries)
        if self.include_original and original_topic and original_topic not in queries:
            queries.append(original_topic)

        logger.info(f"开始并行搜索: {len(queries)} 个查询, max_workers={self.max_workers}")

        all_results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._execute_single_search, q, max_results_per_query): q
                for q in queries
            }
            for future in as_completed(futures):
                query = futures[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    logger.info(f"子查询完成 [{query[:40]}]: {len(results)} 条")
                except Exception as e:
                    logger.error(f"子查询失败 [{query[:40]}]: {e}")

        merged = self._merge_and_dedupe(all_results)
        logger.info(f"并行搜索完成: {len(all_results)} 条原始 → {len(merged)} 条去重")
        return merged

    def _execute_single_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.search_service:
            return []
        result = self.search_service.search(query, max_results=max_results)
        if result.get('success') and result.get('results'):
            for item in result['results']:
                item['_sub_query'] = query
            return result['results']
        return []

    @staticmethod
    def _merge_and_dedupe(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        merged = []
        for item in results:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(item)
            elif not url:
                merged.append(item)
        return merged

    # ── 完整流程 ──────────────────────────────

    def run(self, topic: str, target_audience: str = '', max_results: int = 15) -> Dict[str, Any]:
        """完整的子查询并行研究流程"""
        # Step 1: 可选的初始搜索获取 context
        context = ''
        if self.context_enabled and self.search_service:
            try:
                initial = self.search_service.search(topic, max_results=3)
                if initial.get('success') and initial.get('results'):
                    context = '\n'.join([
                        f"- {r.get('title', '')}: {(r.get('content', '') or '')[:200]}"
                        for r in initial['results'][:3]
                    ])
                    logger.info(f"初始搜索完成，获取 context: {len(context)} 字符")
            except Exception as e:
                logger.warning(f"初始搜索失败，继续无 context 生成: {e}")

        # Step 2: 生成子查询
        sub_queries = self.generate_sub_queries(topic, target_audience, context)

        # Step 3: 并行搜索
        per_query = max(3, max_results // max(len(sub_queries), 1))
        results = self.parallel_search(sub_queries, original_topic=topic, max_results_per_query=per_query)

        return {
            'results': results[:max_results],
            'sub_queries': sub_queries,
            'stats': {
                'sub_query_count': len(sub_queries),
                'total_raw_results': len(results),
                'final_results': min(len(results), max_results),
                'context_used': bool(context),
            },
        }
