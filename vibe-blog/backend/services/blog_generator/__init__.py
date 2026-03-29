"""
长文博客生成器 - Multi-Agent 协同生成系统

基于 LangGraph 实现的技术博客自动生成系统，包含以下 Agent:
- Researcher: 联网搜索收集背景资料
- Planner: 大纲规划
- Writer: 内容撰写
- Coder: 代码示例生成
- Artist: 配图生成
- Questioner: 追问深化
- Reviewer: 质量审核
- Assembler: 文档组装
"""

from .generator import BlogGenerator
from .services.search_service import SearchService, init_search_service, get_search_service

__all__ = [
    'BlogGenerator',
    'SearchService',
    'init_search_service',
    'get_search_service',
]
