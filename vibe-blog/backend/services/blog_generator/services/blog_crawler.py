"""
75.06 BlogCrawler — 高质量博客定时爬取器

使用 Crawl4AI 主动爬取高质量博客域名的最新文章，
存入 LocalMaterialStore。Crawl4AI 未安装时优雅降级。
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 高质量博客域名 → 文章列表页 URL
HIGH_QUALITY_BLOG_DOMAINS: Dict[str, str] = {
    # AI / LLM 官方博客
    "anthropic.com": "https://www.anthropic.com/blog",
    "openai.com": "https://openai.com/blog",
    "blog.google": "https://blog.google/technology/ai/",
    "ai.meta.com": "https://ai.meta.com/blog/",
    "huggingface.co": "https://huggingface.co/blog",
    "deepmind.google": "https://deepmind.google/discover/blog/",
    "mistral.ai": "https://mistral.ai/news/",
    # 开发者技术博客
    "blog.langchain.dev": "https://blog.langchain.dev",
    "github.blog": "https://github.blog",
    "vercel.com": "https://vercel.com/blog",
    # 技术媒体 / 个人博客
    "lilianweng.github.io": "https://lilianweng.github.io",
    "simonwillison.net": "https://simonwillison.net",
}


def _crawl4ai_available() -> bool:
    """检查 Crawl4AI 是否已安装"""
    try:
        import crawl4ai  # noqa: F401
        return True
    except ImportError:
        return False


class BlogCrawler:
    """高质量博客定时爬取器"""

    def __init__(
        self,
        store=None,
        domains: Optional[Dict[str, str]] = None,
        max_per_domain: int = 10,
    ):
        self.store = store
        self.domains = domains or HIGH_QUALITY_BLOG_DOMAINS
        self.max_per_domain = max_per_domain

    def filter_new_urls(self, urls: List[str]) -> List[str]:
        """过滤出素材库中不存在的 URL"""
        if not self.store:
            return urls
        return [u for u in urls if not self.store.has_url(u)]

    async def crawl_all(self) -> Dict:
        """爬取所有高质量博客域名

        Returns:
            {"total_new": int, "domains": {domain: count}}
        """
        if not _crawl4ai_available():
            logger.warning("Crawl4AI 未安装，跳过主动爬取")
            return {"total_new": 0, "domains": {}, "error": "crawl4ai not installed"}

        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        stats = {"total_new": 0, "domains": {}}
        browser_config = BrowserConfig(headless=True)
        crawl_config = CrawlerRunConfig(
            word_count_threshold=200,
            excluded_tags=["nav", "footer", "aside", "header"],
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            for domain, index_url in self.domains.items():
                try:
                    count = await self._crawl_domain(
                        crawler, domain, index_url, crawl_config
                    )
                    stats["domains"][domain] = count
                    stats["total_new"] += count
                except Exception as e:
                    logger.warning(f"爬取 {domain} 失败: {e}")
                    stats["domains"][domain] = 0

        logger.info(f"主动爬取完成: 新增 {stats['total_new']} 篇")
        return stats

    async def _crawl_domain(
        self, crawler, domain: str, index_url: str, crawl_config
    ) -> int:
        """爬取单个域名的最新文章"""
        # Step 1: 爬取列表页
        result = await crawler.arun(url=index_url, config=crawl_config)
        if not result.success:
            logger.warning(f"{domain} 列表页爬取失败")
            return 0

        # Step 2: 提取文章链接
        article_urls = self._extract_article_urls(result, domain)

        # Step 3: 过滤已有
        new_urls = self.filter_new_urls(article_urls)
        new_urls = new_urls[: self.max_per_domain]

        if not new_urls:
            return 0

        # Step 4: 批量爬取新文章
        results = await crawler.arun_many(urls=new_urls, config=crawl_config)
        count = 0
        for r in results:
            if r.success and r.markdown and len(r.markdown) > 500:
                self.store.save({
                    "url": r.url,
                    "domain": domain,
                    "title": getattr(r, "title", "") or "",
                    "content_md": r.markdown,
                    "summary": r.markdown[:300],
                    "keywords": [],
                })
                count += 1

        logger.info(f"{domain}: 新增 {count} 篇")
        return count

    @staticmethod
    def _extract_article_urls(result, domain: str) -> List[str]:
        """从列表页提取文章 URL"""
        import re
        urls = []
        if not result.markdown:
            return urls
        # 从 Markdown 中提取链接
        links = re.findall(r'\[.*?\]\((https?://[^)]+)\)', result.markdown)
        for link in links:
            if domain in link and link not in urls:
                urls.append(link)
        return urls
