"""Serper Google 搜索工具适配器 — 包装 SerperSearchService 为 BaseSearchTool（102.08）"""

import os
from typing import Optional

from .base import BaseSearchTool, SearchResponse, SearchResult


class SerperSearchTool(BaseSearchTool):
    """Serper Google Search 适配器"""

    name = "serper_search"

    def __init__(self, api_key: str = "", timeout: int = 10, max_results: int = 10, **kwargs):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.timeout = timeout
        self.max_results = max_results

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        try:
            from ..services.serper_search_service import SerperSearchService
            svc = SerperSearchService(api_key=self.api_key, config={"timeout": self.timeout})
            raw = svc.search(query, max_results=max_results or self.max_results)
            if not raw.get("success"):
                return SearchResponse(success=False, error=raw.get("error", "unknown"))
            results = [
                SearchResult(title=r.get("title", ""), url=r.get("url", r.get("link", "")), content=r.get("content", r.get("snippet", "")), source="serper")
                for r in raw.get("results", [])
            ]
            return SearchResponse(success=True, results=results, summary=raw.get("summary", ""))
        except Exception as e:
            return SearchResponse(success=False, error=str(e))
