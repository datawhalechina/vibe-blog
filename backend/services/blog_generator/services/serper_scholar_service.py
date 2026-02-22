"""
Google Scholar search service via Serper API.

Uses the /scholar endpoint of google.serper.dev to retrieve
academic publication metadata including citation counts,
publication info, year, and PDF URLs.
"""

import logging
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SerperScholarService:
    """Google Scholar search service via Serper API"""

    SCHOLAR_URL = "https://google.serper.dev/scholar"
    MAX_RETRIES = 3
    RETRY_BASE_WAIT = 2

    def __init__(self, api_key: str = "", timeout: int = 10, max_results: int = 10):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.timeout = timeout
        self.max_results = max_results

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = None) -> Dict[str, Any]:
        """
        Search Google Scholar for a single query.

        Returns:
            {"success": bool, "results": [...], "summary": str, "error": str|None}
        """
        if not self.api_key:
            return {"success": False, "results": [], "summary": "",
                    "error": "Serper API Key not configured"}

        max_results = max_results or self.max_results
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": min(max_results, 20)}

        logger.info(f"Google Scholar search: {query}")

        last_err = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(
                    self.SCHOLAR_URL, json=payload, headers=headers,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                results = self._parse_scholar_results(data)
                logger.info(f"Scholar search done: {len(results)} results")
                return {
                    "success": True,
                    "results": results,
                    "summary": self._generate_summary(results),
                    "error": None,
                }
            except requests.exceptions.RequestException as e:
                last_err = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BASE_WAIT * (2 ** attempt)
                    logger.warning(
                        f"Scholar request failed (attempt {attempt+1}): {e}, "
                        f"retrying in {wait}s"
                    )
                    time.sleep(wait)

        err_msg = f"Scholar API request failed: {last_err}"
        logger.error(err_msg)
        return {"success": False, "results": [], "summary": "", "error": err_msg}

    def search_batch(
        self, queries: List[str], max_results: int = None, max_workers: int = 3
    ) -> Dict[str, Any]:
        """Search Google Scholar for multiple queries in parallel."""
        if not queries:
            return {"success": True, "results": [], "summary": "", "error": None}

        all_results = []
        errors = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.search, q, max_results): q for q in queries
            }
            for future in futures:
                try:
                    result = future.result()
                    if result["success"]:
                        all_results.extend(result["results"])
                    else:
                        errors.append(result.get("error", ""))
                except Exception as e:
                    errors.append(str(e))

        return {
            "success": len(all_results) > 0,
            "results": all_results,
            "summary": self._generate_summary(all_results),
            "error": "; ".join(errors) if errors and not all_results else None,
        }

    def _parse_scholar_results(self, data: dict) -> List[Dict[str, Any]]:
        """Parse Serper Scholar API response into structured results."""
        if "organic" not in data:
            return []

        results = []
        for page in data["organic"]:
            result = {
                "title": page.get("title", ""),
                "url": page.get("link", ""),
                "snippet": page.get("snippet", ""),
                "source": "Google Scholar",
                "publication_info": page.get("publicationInfo", ""),
                "year": page.get("year", ""),
                "cited_by": page.get("citedBy", 0),
                "pdf_url": page.get("pdfUrl", ""),
            }
            results.append(result)

        return results

    def _generate_summary(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return ""
        parts = []
        for r in results:
            line = f"[Scholar] {r.get('title', '')}"
            if r.get("year"):
                line += f" ({r['year']})"
            if r.get("cited_by"):
                line += f" [cited: {r['cited_by']}]"
            if r.get("snippet"):
                line += f"\n{r['snippet'][:500]}"
            parts.append(line)
        return "\n\n---\n\n".join(parts)
