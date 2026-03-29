"""
vibe-reviewer API 路由

所有 API 使用 /api/reviewer/ 前缀，与现有 /api/blog/ 隔离
"""

from .routes import register_reviewer_routes

__all__ = ['register_reviewer_routes']
