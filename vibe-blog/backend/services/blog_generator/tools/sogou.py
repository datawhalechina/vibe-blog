"""搜狗搜索工具适配器 — 包装 SogouSearchService 为 BaseSearchTool（102.08）"""

import os
from typing import Optional

from .base import BaseSearchTool, SearchResponse, SearchResult


class SogouSearchTool(BaseSearchTool):
    """搜狗搜索（腾讯云 SearchPro）适配器"""

    name = "sogou_search"

    def __init__(self, secret_id: str = "", secret_key: str = "", timeout: int = 10, max_results: int = 10, **kwargs):
        self.secret_id = secret_id or os.getenv("TENCENTCLOUD_SECRET_ID", "")
        self.secret_key = secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY", "")
        self.timeout = timeout
        self.max_results = max_results

    def is_available(self) -> bool:
        return bool(self.secret_id and self.secret_key)

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        try:
            from ..services.sogou_search_service import SogouSearchService
            svc = SogouSearchService(secret_id=self.secret_id, secret_key=self.secret_key, timeout=self.timeout, max_results=max_results or self.max_results)
            raw = svc.search(query, max_results=max_results or self.max_results)
            if not raw.get("success"):
                return SearchResponse(success=False, error=raw.get("error", "unknown"))
            results = [
                SearchResult(title=r.get("title", ""), url=r.get("url", ""), content=r.get("content", ""), source="sogou", source_type=r.get("source_type", "web"))
                for r in raw.get("results", [])
            ]
            return SearchResponse(success=True, results=results, summary=raw.get("summary", ""))
        except Exception as e:
            return SearchResponse(success=False, error=str(e))
