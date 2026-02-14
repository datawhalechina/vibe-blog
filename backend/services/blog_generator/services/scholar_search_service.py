"""
Google Scholar 学术搜索服务 — 通过 Serper Scholar API

复用 SERPER_API_KEY，调用 https://google.serper.dev/scholar 端点。
返回论文标题、摘要、发表年份、引用数、PDF 链接等学术元数据。

75.09 Google Scholar 学术搜索集成（来源：95.00 P1-1）
"""
import logging
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_scholar_service: Optional["ScholarSearchService"] = None


class ScholarSearchService:
    """Google Scholar 学术搜索 — 通过 Serper Scholar API"""

    SCHOLAR_URL = "https://google.serper.dev/scholar"
    MAX_RETRIES = 3
    RETRY_BASE_WAIT = 2

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.config = config or {}
        self.timeout = int(self.config.get("timeout", os.environ.get("SERPER_TIMEOUT", "10")))
        self.default_max = int(self.config.get("max_results", 5))

    def is_available(self) -> bool:
        return bool(self.api_key)

    # ---- 搜索 ----

    def search(
        self,
        query: str,
        max_results: int = None,
    ) -> Dict[str, Any]:
        """搜索 Google Scholar

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            搜索结果字典，包含学术元数据
        """
        if not self.api_key:
            return {"success": False, "results": [], "error": "Serper API Key 未配置"}

        max_results = max_results or self.default_max
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": min(max_results, 20)}

        logger.info(f"Scholar 搜索: {query}")

        last_err = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(
                    self.SCHOLAR_URL, json=payload, headers=headers, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()

                results = self._parse_results(data)
                logger.info(f"Scholar 搜索完成: {len(results)} 条结果")
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
                    logger.warning(f"Scholar 请求失败 (attempt {attempt+1}): {e}，{wait}s 后重试")
                    time.sleep(wait)

        err_msg = f"Scholar API 请求失败: {last_err}"
        logger.error(err_msg)
        return {"success": False, "results": [], "error": err_msg}

    def batch_search(
        self,
        queries: List[str],
        max_results_per_query: int = 5,
        max_workers: int = 3,
    ) -> Dict[str, Any]:
        """批量并行搜索多个学术查询

        Args:
            queries: 查询列表
            max_results_per_query: 每个查询的最大结果数
            max_workers: 最大并行线程数

        Returns:
            合并去重后的搜索结果
        """
        if not self.api_key:
            return {"success": False, "results": [], "error": "Serper API Key 未配置"}

        if not queries:
            return {"success": True, "results": [], "error": None}

        workers = min(len(queries), max_workers)
        all_results: List[Dict[str, Any]] = []
        errors: List[str] = []

        logger.info(f"Scholar 批量搜索: {len(queries)} 个查询, 并行度={workers}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self.search, q, max_results_per_query): q
                for q in queries
            }
            for future in as_completed(futures):
                query = futures[future]
                try:
                    result = future.result()
                    if result.get("success"):
                        all_results.extend(result["results"])
                    elif result.get("error"):
                        errors.append(f"[{query}] {result['error']}")
                except Exception as e:
                    errors.append(f"[{query}] {e}")
                    logger.error(f"Scholar 批量搜索失败 [{query}]: {e}")

        # 去重（按 URL）
        seen_urls: set = set()
        unique: List[Dict[str, Any]] = []
        for item in all_results:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(item)

        logger.info(f"Scholar 批量搜索完成: {len(all_results)} 条 → 去重后 {len(unique)} 条")

        return {
            "success": True,
            "results": unique,
            "summary": self._generate_summary(unique),
            "error": "; ".join(errors) if errors else None,
        }

    # ---- 解析 ----

    def _parse_results(self, data: dict) -> List[Dict[str, Any]]:
        results = []
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("pdfUrl", item.get("link", "")),
                "content": item.get("snippet", ""),
                "source": "Google Scholar",
                "year": item.get("year", ""),
                "cited_by": item.get("citedBy", 0),
                "publication": item.get("publicationInfo", ""),
            })
        return results

    def _generate_summary(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return ""
        parts = []
        for item in results:
            year = f" ({item['year']})" if item.get("year") else ""
            cited = f" [cited: {item['cited_by']}]" if item.get("cited_by") else ""
            pub = f" — {item['publication']}" if item.get("publication") else ""
            parts.append(
                f"[Scholar] {item.get('title', '')}{year}{cited}{pub}\n"
                f"{item.get('content', '')[:800]}"
            )
        return "\n\n---\n\n".join(parts)


# ---- 全局实例管理 ----

def init_scholar_service(config: Dict[str, Any] = None) -> ScholarSearchService:
    global _scholar_service
    config = config or {}
    api_key = config.get("SERPER_API_KEY") or os.environ.get("SERPER_API_KEY", "")
    _scholar_service = ScholarSearchService(api_key=api_key, config=config)
    if api_key:
        logger.info("Google Scholar 搜索服务已初始化（复用 Serper API Key）")
    else:
        logger.info("Scholar 服务: 未配置 SERPER_API_KEY，学术搜索不可用")
    return _scholar_service


def get_scholar_service() -> Optional[ScholarSearchService]:
    """获取 Scholar 服务实例（懒加载）"""
    global _scholar_service
    if _scholar_service is None:
        api_key = os.environ.get("SERPER_API_KEY", "")
        if api_key:
            _scholar_service = ScholarSearchService(api_key=api_key)
            logger.info("Google Scholar 搜索服务已懒加载初始化")
    return _scholar_service
