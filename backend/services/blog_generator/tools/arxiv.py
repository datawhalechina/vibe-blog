"""arXiv 搜索工具适配器 — 包装 ArxivService 为 BaseSearchTool（102.08）"""

from .base import BaseSearchTool, SearchResponse, SearchResult


class ArxivSearchTool(BaseSearchTool):
    """arXiv 学术论文搜索适配器"""

    name = "arxiv_search"

    def __init__(self, max_results: int = 5, **kwargs):
        self.max_results = max_results

    def is_available(self) -> bool:
        return True  # arXiv API 免费无需 Key

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        try:
            from ..services.arxiv_service import ArxivService
            svc = ArxivService()
            raw = svc.search(query, max_results=max_results or self.max_results)
            if not raw.get("success"):
                return SearchResponse(success=False, error=raw.get("error", "unknown"))
            results = [
                SearchResult(title=r.get("title", ""), url=r.get("url", ""), content=r.get("content", r.get("summary", "")), source="arxiv", source_type="arxiv")
                for r in raw.get("results", [])
            ]
            return SearchResponse(success=True, results=results, summary=raw.get("summary", ""))
        except Exception as e:
            return SearchResponse(success=False, error=str(e))
