"""
vibe-reviewer - Git 教程质量评估服务

作为 vibe-blog 的新功能模块，提供：
- Git 仓库教程批量评估
- 多维度质量评分 (深度/质量/可读性)
- 搜索增强评估 (参考 Agentic Reviewer)
- 可操作的改进建议
- 图片多模态理解与审核

注意：本模块独立于 blog_generator，不修改现有功能
"""

from .reviewer_service import (
    ReviewerService,
    init_reviewer_service,
    get_reviewer_service
)

__all__ = [
    'ReviewerService',
    'init_reviewer_service',
    'get_reviewer_service',
]
