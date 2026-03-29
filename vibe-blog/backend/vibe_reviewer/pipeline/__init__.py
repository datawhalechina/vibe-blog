"""
评估流水线模块

- analyzer: 内容分析器 (类型识别+摘要+搜索词)
- search_agent: 多视角搜索代理 (复用 search_service)
- reference_manager: 参考资料管理 (相关性评估+智能摘要)
- score_aggregator: 分数聚合器 (多维度→最终分数)
"""

from .analyzer import ContentAnalyzer
from .search_agent import SearchAgent
from .reference_manager import ReferenceManager
from .score_aggregator import ScoreAggregator

__all__ = [
    'ContentAnalyzer',
    'SearchAgent',
    'ReferenceManager',
    'ScoreAggregator',
]
