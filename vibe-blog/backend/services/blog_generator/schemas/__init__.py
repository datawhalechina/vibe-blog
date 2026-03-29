"""
数据模型模块 - Pydantic 模型和 TypedDict 定义
"""

from .state import (
    SharedState,
    SectionOutline,
    SectionContent,
    CodeBlock,
    ImageResource,
    VaguePoint,
    QuestionResult,
    ReviewIssue,
    BlogOutline,
    KnowledgeGap,
    SearchHistoryItem,
    create_initial_state,
    get_max_search_count,
)

__all__ = [
    'SharedState',
    'SectionOutline',
    'SectionContent',
    'CodeBlock',
    'ImageResource',
    'VaguePoint',
    'QuestionResult',
    'ReviewIssue',
    'BlogOutline',
    'KnowledgeGap',
    'SearchHistoryItem',
    'create_initial_state',
    'get_max_search_count',
]
