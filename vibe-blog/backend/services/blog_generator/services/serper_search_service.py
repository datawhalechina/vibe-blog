"""
Google 搜索服务 — 通过 Serper API

来源：MiroThinker searching_google_mcp_server.py（跳过 MCP 壳，直接调 API）
Serper (https://serper.dev) 提供 Google 搜索 API，免费额度 2,500 次/月。

75.02 Serper Google 搜索集成
"""
import logging
import os
import re
import time
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_serper_service: Optional["SerperSearchService"] = None


class SerperSearchService:
    """Google 搜索服务 — 通过 Serper API"""

    BASE_URL = "https://google.serper.dev/search"
    MAX_RETRIES = 3
    RETRY_BASE_WAIT = 2

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.config = config or {}
        self.timeout = int(self.config.get("SERPER_TIMEOUT", os.environ.get("SERPER_TIMEOUT", "10")))
        self.default_max = int(self.config.get("SERPER_MAX_RESULTS", os.environ.get("SERPER_MAX_RESULTS", "10")))

    def is_available(self) -> bool:
        return bool(self.api_key)

    # ---- 搜索 ----

    def search(
        self,
        query: str,
        max_results: int = None,
        gl: str = None,
        hl: str = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "results": [], "summary": "", "error": "Serper API Key 未配置"}

        if gl is None or hl is None:
            _gl, _hl = self.detect_search_locale(query)
            gl = gl or _gl
            hl = hl or _hl

        max_results = max_results or self.default_max

        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": gl, "hl": hl, "num": min(max_results, 20)}

        logger.info(f"Serper Google 搜索: {query} (gl={gl}, hl={hl})")

        # 重试
        last_err = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()

                results = self._parse_results(data)
                logger.info(f"Serper 搜索完成: {len(results)} 条结果")
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
                    logger.warning(f"Serper 请求失败 (attempt {attempt+1}): {e}，{wait}s 后重试")
                    time.sleep(wait)

        err_msg = f"Serper API 请求失败: {last_err}"
        logger.error(err_msg)
        return {"success": False, "results": [], "summary": "", "error": err_msg}

    # ---- 解析 ----

    def _parse_results(self, data: dict) -> List[Dict[str, Any]]:
        results = []

        # Answer Box
        ab = data.get("answerBox")
        if ab:
            results.append({
                "title": ab.get("title", "Google Answer"),
                "url": ab.get("link", ""),
                "content": ab.get("snippet", ab.get("answer", "")),
                "source": "Google Answer Box",
            })

        # Knowledge Graph
        kg = data.get("knowledgeGraph")
        if kg:
            desc = kg.get("description", "")
            attrs = kg.get("attributes", {})
            if attrs:
                attr_str = " | ".join(f"{k}: {v}" for k, v in list(attrs.items())[:5])
                desc = f"{desc}\n{attr_str}" if desc else attr_str
            if desc:
                results.append({
                    "title": kg.get("title", "Knowledge Graph"),
                    "url": kg.get("descriptionLink", ""),
                    "content": desc,
                    "source": "Google Knowledge Graph",
                })

        # Organic
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "content": item.get("snippet", ""),
                "source": "Google",
            })

        return results

    def _generate_summary(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return ""
        parts = []
        for item in results:
            parts.append(f"[{item.get('source', 'Google')}] {item.get('title', '')}\n{item.get('content', '')[:800]}")
        return "\n\n---\n\n".join(parts)

    # ---- 工具方法 ----

    @staticmethod
    def detect_search_locale(query: str) -> tuple:
        """检测查询语言，返回 (gl, hl)"""
        if re.search(r"[\u4e00-\u9fff]", query):
            return ("cn", "zh-cn")
        return ("us", "en")


# ---- 全局实例管理 ----

def init_serper_service(config: Dict[str, Any] = None) -> SerperSearchService:
    global _serper_service
    config = config or {}
    api_key = config.get("SERPER_API_KEY") or os.environ.get("SERPER_API_KEY", "")
    _serper_service = SerperSearchService(api_key=api_key, config=config)
    if api_key:
        logger.info("Serper Google 搜索服务已初始化")
    else:
        logger.info("Serper 服务: 未配置 API Key，Google 搜索不可用")
    return _serper_service


def get_serper_service() -> Optional[SerperSearchService]:
    return _serper_service
