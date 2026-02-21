"""智谱搜索工具适配器 — 包装 SearchService 为 BaseSearchTool（102.08）"""

import os
from typing import Optional

from .base import BaseSearchTool, SearchResponse, SearchResult


class ZhipuSearchTool(BaseSearchTool):
    """智谱 Web Search 适配器"""

    name = "zhipu_search"

    def __init__(self, api_key: str = "", api_base: str = "", search_engine: str = "search_pro_quark", max_results: int = 5, **kwargs):
        self.api_key = api_key or os.getenv("ZAI_SEARCH_API_KEY", "")
        self.api_base = api_base or os.getenv("ZAI_SEARCH_API_BASE", "")
        self.search_engine = search_engine
        self.max_results = max_results

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        try:
            from ..services.search_service import SearchService
            svc = SearchService(api_key=self.api_key, config={"api_base": self.api_base, "search_engine": self.search_engine})
            raw = svc.search(query, max_results=max_results or self.max_results)
            if not raw.get("success"):
                return SearchResponse(success=False, error=raw.get("error", "unknown"))
            results = [
                SearchResult(title=r.get("title", ""), url=r.get("source", r.get("url", "")), content=r.get("content", ""), source="zhipu")
                for r in raw.get("results", [])
            ]
            return SearchResponse(success=True, results=results, summary=raw.get("summary", ""))
        except Exception as e:
            return SearchResponse(success=False, error=str(e))
