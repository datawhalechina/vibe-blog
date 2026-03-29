"""
数据库模型模块

新增表 (不修改现有表):
- tutorials: 教程表
- chapters: 章节表 (含原文存储)
- issues: 问题表
- images: 图片表 (多模态结果)
- search_references: 搜索参考资料表
- evaluation_history: 评估历史表
"""

from .reviewer_models import (
    init_reviewer_tables,
    TutorialModel,
    ChapterModel,
    IssueModel,
    ImageModel,
)

__all__ = [
    'init_reviewer_tables',
    'TutorialModel',
    'ChapterModel',
    'IssueModel',
    'ImageModel',
]
