"""
数据模型模块 - Pydantic 模型和 TypedDict 定义
"""

from .outputs import (
    AudienceAnalysis,
    BlogOutline,
    CodeBlock,
    ImageResource,
    InformationArchitecture,
    InstructionalAnalysis,
    KnowledgeGap,
    LearningObjective,
    QuestionResult,
    ReviewIssue,
    SearchHistoryItem,
    SearchResult,
    SectionContent,
    SectionOutline,
    VaguePoint,
    VerbatimDataItem,
)
from .state import (
    SharedState,
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
    'LearningObjective',
    'AudienceAnalysis',
    'VerbatimDataItem',
    'InstructionalAnalysis',
    'InformationArchitecture',
    'SearchResult',
    'create_initial_state',
    'get_max_search_count',
]
