"""
搜索代理 - 多视角搜索

复用 vibe-blog 的 search_service
"""
import logging
from typing import List, Dict, Any, Optional

from ..schemas import SearchResult, ContentSummary

logger = logging.getLogger(__name__)


class SearchAgent:
    """
    搜索代理
    
    复用 vibe-blog 的搜索服务，执行多视角搜索
    """
    
    def __init__(self, search_service=None):
        """
        初始化搜索代理
        
        Args:
            search_service: 搜索服务实例 (复用 vibe-blog)
        """
        self.search_service = search_service
    
    def search(
        self, 
        queries: List[str], 
        max_results_per_query: int = 3
    ) -> List[SearchResult]:
        """
        执行搜索
        
        Args:
            queries: 搜索查询列表
            max_results_per_query: 每个查询的最大结果数
            
        Returns:
            搜索结果列表
        """
        if not self.search_service:
            logger.warning("搜索服务不可用")
            return []
        
        all_results = []
        seen_urls = set()
        
        for query in queries:
            try:
                results = self._execute_search(query, max_results_per_query)
                
                for result in results:
                    # 去重
                    if result.source_url in seen_urls:
                        continue
                    seen_urls.add(result.source_url)
                    all_results.append(result)
                    
            except Exception as e:
                logger.warning(f"搜索失败: {query}, 错误: {e}")
        
        logger.info(f"搜索完成: {len(queries)} 个查询, {len(all_results)} 个结果")
        return all_results
    
    def _execute_search(self, query: str, max_results: int) -> List[SearchResult]:
        """执行单个搜索"""
        try:
            # 调用搜索服务
            if hasattr(self.search_service, 'search'):
                response = self.search_service.search(query, max_results=max_results)
            else:
                logger.warning("搜索服务没有 search 方法")
                return []
            
            # 处理返回格式 (vibe-blog 的搜索服务返回 {'success': True, 'results': [...]})
            if isinstance(response, dict):
                if not response.get('success'):
                    logger.warning(f"搜索失败: {response.get('error', '未知错误')}")
                    return []
                raw_results = response.get('results', [])
            else:
                # 兼容直接返回列表的情况
                raw_results = response if isinstance(response, list) else []
            
            # 转换结果格式
            results = []
            for item in raw_results:
                results.append(SearchResult(
                    query=query,
                    source_url=item.get('url', ''),
                    title=item.get('title', ''),
                    snippet=item.get('content', item.get('snippet', '')),
                    relevance_score=0.0,  # 稍后由 ReferenceManager 评估
                ))
            
            logger.info(f"搜索 '{query}' 返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"执行搜索失败: {e}")
            return []
    
    def search_multi_round(
        self, 
        summary: ContentSummary, 
        max_rounds: int = 2,
        results_per_round: int = 5
    ) -> List[SearchResult]:
        """
        多轮搜索
        
        Args:
            summary: 内容摘要
            max_rounds: 最大搜索轮数
            results_per_round: 每轮结果数
            
        Returns:
            搜索结果列表
        """
        all_results = []
        
        # 第一轮：使用生成的搜索查询
        if summary.search_queries:
            round1_results = self.search(
                summary.search_queries[:3], 
                max_results_per_query=results_per_round // 3 + 1
            )
            all_results.extend(round1_results)
        
        # 第二轮：使用关键术语
        if max_rounds >= 2 and summary.key_terms:
            term_queries = [f"{summary.topic} {term}" for term in summary.key_terms[:2]]
            round2_results = self.search(
                term_queries,
                max_results_per_query=2
            )
            all_results.extend(round2_results)
        
        return all_results
