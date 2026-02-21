"""httpx 爬虫工具适配器 — 包装 HttpxScraper 为 BaseCrawlTool（102.08）"""

from typing import Optional

from .base import BaseCrawlTool


class HttpxCrawlTool(BaseCrawlTool):
    """httpx 降级爬虫适配器"""

    name = "httpx_scraper"

    def __init__(self, timeout: int = 20, **kwargs):
        self.timeout = timeout

    def scrape(self, url: str) -> Optional[str]:
        try:
            from ..services.deep_scraper import HttpxScraper
            scraper = HttpxScraper(timeout=self.timeout)
            return scraper.scrape(url)
        except Exception:
            return None
