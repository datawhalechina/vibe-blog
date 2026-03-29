"""Jina Reader 爬虫工具适配器 — 包装 JinaReader 为 BaseCrawlTool（102.08）"""

import os
from typing import Optional

from .base import BaseCrawlTool


class JinaCrawlTool(BaseCrawlTool):
    """Jina Reader 爬虫适配器"""

    name = "jina_reader"

    def __init__(self, api_key: str = "", timeout: int = 30, **kwargs):
        self.api_key = api_key or os.getenv("JINA_API_KEY", "")
        self.timeout = timeout

    def scrape(self, url: str) -> Optional[str]:
        try:
            from ..services.jina_reader import JinaReader
            reader = JinaReader(api_key=self.api_key, timeout=self.timeout)
            return reader.scrape(url)
        except Exception:
            return None
