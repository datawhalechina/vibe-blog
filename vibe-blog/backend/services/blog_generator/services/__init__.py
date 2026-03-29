"""
博客生成器服务模块
"""

from .search_service import SearchService, init_search_service, get_search_service

__all__ = [
    'SearchService',
    'init_search_service',
    'get_search_service',
]
