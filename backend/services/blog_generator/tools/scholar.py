"""Google Scholar search tool adapter -- wraps SerperScholarService as BaseSearchTool"""

import os
from typing import Optional

from .base import BaseSearchTool, SearchResponse, SearchResult


class ScholarSearchTool(BaseSearchTool):
    """Google Scholar search adapter via Serper API"""

    name = "scholar_search"

    def __init__(self, api_key: str = "", timeout: int = 10, max_results: int = 10, **kwargs):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.timeout = timeout
        self.max_results = max_results

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        try:
            from ..services.serper_scholar_service import SerperScholarService
            svc = SerperScholarService(
                api_key=self.api_key, timeout=self.timeout,
                max_results=max_results or self.max_results
            )
            raw = svc.search(query, max_results=max_results or self.max_results)
            if not raw.get("success"):
                return SearchResponse(success=False, error=raw.get("error", "unknown"))
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", r.get("link", "")),
                    content=self._format_scholar_content(r),
                    source="scholar",
                    source_type="scholar",
                )
                for r in raw.get("results", [])
            ]
            return SearchResponse(
                success=True, results=results, summary=raw.get("summary", "")
            )
        except Exception as e:
            return SearchResponse(success=False, error=str(e))

    @staticmethod
    def _format_scholar_content(r: dict) -> str:
        """Format scholar result into readable content string."""
        parts = []
        if r.get("snippet"):
            parts.append(r["snippet"])
        if r.get("publication_info"):
            parts.append(f"Publication: {r['publication_info']}")
        if r.get("year"):
            parts.append(f"Year: {r['year']}")
        if r.get("cited_by"):
            parts.append(f"Cited by: {r['cited_by']}")
        if r.get("pdf_url"):
            parts.append(f"PDF: {r['pdf_url']}")
        return " | ".join(parts) if parts else ""
