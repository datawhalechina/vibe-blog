"""
75.03 Jina Reader — 深度抓取搜索结果原文

使用 Jina Reader API (https://r.jina.ai/{url}) 获取干净的 Markdown 文本。
支持 4 次重试（指数退避），API Key 未配置时使用免费模式。
"""
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

JINA_BASE_URL = "https://r.jina.ai/"


class JinaReader:
    """Jina Reader API 抓取器"""

    def __init__(
        self,
        api_key: str = None,
        timeout: int = 30,
        max_retries: int = 4,
        base_wait: float = 1.0,
    ):
        self.api_key = api_key or os.getenv("JINA_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_wait = base_wait

    def _build_url(self, target_url: str) -> str:
        return f"{JINA_BASE_URL}{target_url}"

    def _build_headers(self) -> dict:
        headers = {
            "Accept": "text/markdown",
            "X-Return-Format": "markdown",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def scrape(self, url: str) -> Optional[str]:
        """抓取 URL 全文，返回 Markdown 文本

        Args:
            url: 目标 URL

        Returns:
            Markdown 文本，失败返回 None
        """
        jina_url = self._build_url(url)
        headers = self._build_headers()

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(
                    jina_url,
                    headers=headers,
                    timeout=self.timeout,
                )
                if resp.status_code == 200 and resp.text.strip():
                    logger.info(f"Jina 抓取成功: {url} ({len(resp.text)} chars)")
                    return resp.text.strip()
                logger.warning(f"Jina 抓取返回 {resp.status_code}: {url}")
            except Exception as e:
                logger.warning(f"Jina 抓取失败 (attempt {attempt + 1}/{self.max_retries}): {e}")

            if attempt < self.max_retries - 1:
                wait = self.base_wait * (2 ** attempt)
                time.sleep(wait)

        logger.error(f"Jina 抓取全部重试失败: {url}")
        return None
