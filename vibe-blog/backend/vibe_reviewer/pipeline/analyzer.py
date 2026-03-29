"""
内容分析器 - 分析内容类型、提取摘要、生成搜索查询

参考 Agentic Reviewer 的多视角搜索策略
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas import ContentSummary, ContentType

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    内容分析器
    
    功能:
    - 识别内容类型
    - 提取主题、核心观点、关键术语
    - 生成多视角搜索查询
    """
    
    def __init__(self, llm_service):
        """
        初始化内容分析器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
        self.pm = get_prompt_manager()
    
    def analyze(self, content: str) -> ContentSummary:
        """
        分析内容
        
        Args:
            content: 待分析内容
            
        Returns:
            内容摘要
        """
        prompt = self.pm.render_analyze(content)
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return self._default_summary(content)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"内容分析失败: {e}")
            return self._default_summary(content)
    
    def _parse_response(self, response: str) -> ContentSummary:
        """解析 LLM 响应"""
        try:
            # 提取 JSON
            response = response.strip()
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                response = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                response = response[start:end].strip()
            
            data = json.loads(response)
            
            # 解析内容类型
            content_type_str = data.get('content_type', 'unknown')
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                content_type = ContentType.UNKNOWN
            
            return ContentSummary(
                topic=data.get('topic', ''),
                content_type=content_type,
                core_points=data.get('core_points', []),
                key_terms=data.get('key_terms', []),
                fact_claims=data.get('fact_claims', []),
                search_queries=data.get('search_queries', []),
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析内容分析结果失败: {e}")
            return self._default_summary("")
    
    def _default_summary(self, content: str) -> ContentSummary:
        """返回默认摘要"""
        # 简单提取一些关键词作为搜索查询
        words = content[:500].split()[:10]
        search_queries = [' '.join(words[:5])] if words else []
        
        return ContentSummary(
            topic="",
            content_type=ContentType.UNKNOWN,
            core_points=[],
            key_terms=[],
            fact_claims=[],
            search_queries=search_queries,
        )
