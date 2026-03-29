"""
参考资料管理器 - 相关性评估与智能摘要

参考 Agentic Reviewer 的相关性分级策略
"""
import logging
from typing import List, Dict, Any, Optional

from ..schemas import SearchResult, ReferenceContext, ContentSummary

logger = logging.getLogger(__name__)


class ReferenceManager:
    """
    参考资料管理器
    
    功能:
    - 评估搜索结果的相关性
    - 智能摘要策略 (高相关下载全文)
    - 管理参考资料上下文
    """
    
    def __init__(self, llm_service=None):
        """
        初始化参考资料管理器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
    
    def evaluate_relevance(
        self, 
        results: List[SearchResult], 
        summary: ContentSummary
    ) -> List[SearchResult]:
        """
        评估搜索结果的相关性
        
        Args:
            results: 搜索结果列表
            summary: 内容摘要
            
        Returns:
            带相关性评分的搜索结果列表
        """
        if not results:
            return []
        
        evaluated_results = []
        
        for result in results:
            # 简单的相关性评估 (基于关键词匹配)
            score = self._calculate_relevance(result, summary)
            result.relevance_score = score
            evaluated_results.append(result)
        
        # 按相关性排序
        evaluated_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return evaluated_results
    
    def _calculate_relevance(self, result: SearchResult, summary: ContentSummary) -> float:
        """计算相关性得分"""
        score = 0.0
        
        text = (result.title + ' ' + result.snippet).lower()
        
        # 主题匹配
        if summary.topic and summary.topic.lower() in text:
            score += 0.3
        
        # 关键术语匹配
        matched_terms = 0
        for term in summary.key_terms:
            if term.lower() in text:
                matched_terms += 1
        if summary.key_terms:
            score += 0.4 * (matched_terms / len(summary.key_terms))
        
        # 核心观点匹配
        matched_points = 0
        for point in summary.core_points:
            # 简单的词重叠检查
            point_words = set(point.lower().split())
            text_words = set(text.split())
            if len(point_words & text_words) >= 2:
                matched_points += 1
        if summary.core_points:
            score += 0.3 * (matched_points / len(summary.core_points))
        
        return min(score, 1.0)
    
    def filter_by_relevance(
        self, 
        results: List[SearchResult], 
        min_score: float = 0.3
    ) -> List[SearchResult]:
        """
        过滤低相关性结果
        
        Args:
            results: 搜索结果列表
            min_score: 最低相关性阈值
            
        Returns:
            过滤后的结果列表
        """
        return [r for r in results if r.relevance_score >= min_score]
    
    def build_context(
        self, 
        summary: ContentSummary, 
        results: List[SearchResult]
    ) -> ReferenceContext:
        """
        构建参考资料上下文
        
        Args:
            summary: 内容摘要
            results: 搜索结果列表
            
        Returns:
            参考资料上下文
        """
        return ReferenceContext(
            summary=summary,
            search_results=results,
            verified_facts=[],
            contradictions=[],
        )
    
    def get_top_references(
        self, 
        results: List[SearchResult], 
        top_k: int = 5
    ) -> List[Dict]:
        """
        获取 Top-K 参考资料 (用于传递给评估 Agents)
        
        Args:
            results: 搜索结果列表
            top_k: 返回数量
            
        Returns:
            参考资料列表 (字典格式)
        """
        top_results = results[:top_k]
        
        return [
            {
                'title': r.title,
                'source_url': r.source_url,
                'snippet': r.snippet,
                'relevance_score': r.relevance_score,
            }
            for r in top_results
        ]
