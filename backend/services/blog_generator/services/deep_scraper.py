"""
75.03 DeepScraper — 深度抓取统一入口

两层架构：
1. JinaReader 抓取全文 Markdown（降级 HttpxScraper）
2. LLM 提取与主题相关的关键信息

对搜索结果 Top N URL 进行深度抓取，结果作为高质量素材注入 Writer。
"""
import logging
import os
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# 已知低质量域名（SEO 垃圾站、内容农场）
LOW_QUALITY_DOMAINS = {
    "csdn.net", "jianshu.com", "360doc.com", "baijiahao.baidu.com",
    "sohu.com", "163.com", "toutiao.com", "zhidao.baidu.com",
    "wenku.baidu.com", "docin.com", "doc88.com",
}

# 高质量域名（优先抓取）
HIGH_QUALITY_DOMAINS = {
    "github.com", "arxiv.org", "openai.com", "anthropic.com",
    "huggingface.co", "pytorch.org", "tensorflow.org",
    "docs.python.org", "developer.mozilla.org",
    "medium.com", "dev.to", "stackoverflow.com",
}


class HttpxScraper:
    """httpx 降级抓取器（带 User-Agent 伪装）"""

    def __init__(self, timeout: int = 20, max_retries: int = 3, base_wait: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_wait = base_wait

    def scrape(
        self,
        url: str,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        deadline: Optional[float] = None,
    ) -> Optional[str]:
        request_timeout = self.timeout if timeout is None else timeout
        retry_limit = self.max_retries if max_retries is None else max(1, max_retries)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }
        for attempt in range(retry_limit):
            remaining = deadline - time.monotonic() if deadline is not None else None
            if remaining is not None and remaining <= 0:
                break
            attempt_timeout = (
                min(request_timeout, max(0.01, remaining))
                if remaining is not None
                else request_timeout
            )
            try:
                resp = requests.get(url, headers=headers, timeout=attempt_timeout)
                if resp.status_code == 200 and resp.text.strip():
                    # 简单提取正文（去除 HTML 标签）
                    text = self._html_to_text(resp.text)
                    if text:
                        logger.info(f"httpx 抓取成功: {url} ({len(text)} chars)")
                        return text
            except Exception as e:
                logger.warning(f"httpx 抓取失败 (attempt {attempt + 1}): {e}")
            if attempt < retry_limit - 1:
                retry_wait = self.base_wait * (2 ** attempt)
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    retry_wait = min(retry_wait, remaining)
                time.sleep(retry_wait)
        return None

    @staticmethod
    def _html_to_text(html: str) -> str:
        """简单 HTML → 纯文本"""
        # PLACEHOLDER_MORE_CONTENT
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text


class DeepScraper:
    """深度抓取统一入口"""

    def __init__(
        self,
        jina_api_key: str = None,
        llm_service=None,
        timeout: int = 30,
        top_n: int = 3,
        max_retries: int = 1,
        total_timeout: float = 60,
        min_successful_sources: Optional[int] = None,
        mini_timeout: float = 8,
        mini_total_timeout: float = 20,
        mini_top_n: int = 1,
    ):
        from services.blog_generator.services.jina_reader import JinaReader
        self.jina = JinaReader(
            api_key=jina_api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.httpx = HttpxScraper(timeout=timeout, max_retries=max_retries)
        self.llm_service = llm_service
        self.top_n = top_n
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.total_timeout = max(0.01, total_timeout)
        self.min_successful_sources = (
            max(1, min_successful_sources)
            if min_successful_sources is not None
            else max(1, top_n)
        )
        self.mini_timeout = max(0.01, mini_timeout)
        self.mini_total_timeout = max(0.01, mini_total_timeout)
        self.mini_top_n = max(1, mini_top_n)

        # Goal-directed extractor (feature toggle, default off)
        self._extractor = None
        if os.environ.get("GOAL_EXTRACTION_ENABLED", "false").lower() == "true":
            try:
                from services.blog_generator.services.goal_directed_extractor import GoalDirectedExtractor
                self._extractor = GoalDirectedExtractor(llm_service=llm_service)
                logger.info("Goal-directed extraction enabled")
            except Exception as e:
                logger.warning(f"GoalDirectedExtractor init failed: {e}")

    def scrape_top_n(
        self,
        results: List[Dict],
        topic: str,
        n: int = None,
        goal: str = None,
        preset: str = None,
    ) -> List[Dict]:
        """按共享抓取预算处理 Top N URL，并提炼成功来源。

        Args:
            results: search results
            topic: research topic
            n: max URLs to scrape
            goal: specific extraction goal (used by GoalDirectedExtractor)
        """
        n = n or self.top_n
        request_timeout = self.timeout
        total_timeout = self.total_timeout
        if preset == "mini":
            n = min(n, self.mini_top_n)
            request_timeout = min(request_timeout, self.mini_timeout)
            total_timeout = min(total_timeout, self.mini_total_timeout)

        selected = self._select_urls(results, n)
        if not selected:
            return []

        enriched = []
        scraped_sources = []
        effective_goal = goal or f"收集与「{topic}」相关的关键技术信息、核心概念和实践案例"

        def _extract_one(item: Dict, full_text: str) -> Dict:
            url = item.get("url", "")
            if self._extractor:
                extraction = self._extractor.extract(full_text, effective_goal)
                return {
                    "url": url,
                    "title": item.get("title", ""),
                    "rational": extraction.rational,
                    "evidence": extraction.evidence,
                    "summary": extraction.summary,
                    "extraction_success": extraction.success,
                    "full_text_length": len(full_text),
                }
            else:
                extracted = self._extract_info(full_text, topic)
                return {
                    "url": url,
                    "title": item.get("title", ""),
                    "full_text": full_text,
                    "extracted_info": extracted,
                }

        required_successes = min(self.min_successful_sources, len(selected))
        deadline = time.monotonic() + total_timeout
        for index, item in enumerate(selected):
            if len(scraped_sources) >= required_successes:
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            sources_left = len(selected) - index
            source_deadline = time.monotonic() + (remaining / sources_left)
            url = item.get("url", "")
            try:
                full_text = self._scrape_single(
                    url,
                    timeout=request_timeout,
                    max_retries=self.max_retries,
                    deadline=source_deadline,
                )
                if full_text:
                    scraped_sources.append((item, full_text))
            except Exception as e:
                logger.warning(f"深度抓取任务失败 [{url}]: {e}")

        for item, full_text in scraped_sources:
            try:
                enriched.append(_extract_one(item, full_text))
            except Exception as e:
                logger.warning(
                    f"深度抓取提炼失败 [{item.get('url', '')}]: {e}"
                )

        logger.info(f"深度抓取完成: {len(enriched)}/{len(selected)} 成功（预算模式）")
        return enriched

    def _select_urls(self, results: List[Dict], n: int) -> List[Dict]:
        """筛选 Top N 高质量 URL"""
        if not results:
            return []

        # 过滤低质量 URL
        filtered = [r for r in results if not self._is_low_quality_url(r.get("url", ""))]

        # 按质量排序：高质量域名优先
        def quality_score(r):
            domain = urlparse(r.get("url", "")).netloc.lower()
            base = domain.lstrip("www.")
            if any(hq in base for hq in HIGH_QUALITY_DOMAINS):
                return 0  # 最高优先
            return 1

        filtered.sort(key=quality_score)
        return filtered[:n]

    def _is_low_quality_url(self, url: str) -> bool:
        """检查是否为低质量 URL"""
        if not url:
            return True
        domain = urlparse(url).netloc.lower().lstrip("www.")
        return any(lq in domain for lq in LOW_QUALITY_DOMAINS)

    def _scrape_single(
        self,
        url: str,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        deadline: Optional[float] = None,
    ) -> Optional[str]:
        """抓取单个 URL（Jina → httpx 降级）"""
        # 先尝试 Jina
        scrape_kwargs = {"timeout": timeout, "max_retries": max_retries}
        if deadline is not None:
            scrape_kwargs["deadline"] = deadline
        text = self.jina.scrape(url, **scrape_kwargs)
        if text:
            return text

        if deadline is not None and time.monotonic() >= deadline:
            logger.info(f"Jina 已用完来源预算，跳过 httpx: {url}")
            return None

        # 降级到 httpx
        logger.info(f"Jina 失败，降级 httpx: {url}")
        return self.httpx.scrape(url, **scrape_kwargs)

    def _extract_info(self, full_text: str, topic: str) -> str:
        """使用 LLM 从全文提取与主题相关的信息"""
        truncated = self._truncate(full_text, max_chars=40000)

        if not self.llm_service:
            # 无 LLM 时返回截断后的原文
            return truncated

        prompt = (
            f"从以下文章中提取与「{topic}」相关的关键信息。"
            f"只保留与主题直接相关的内容，去除无关信息。"
            f"输出精炼的要点摘要（中文，500-1500 字）。\n\n"
            f"---\n{truncated}\n---"
        )
        try:
            result = self.llm_service.chat(
                [{"role": "user", "content": prompt}],
                caller="deep_scraper",
            )
            return result or truncated
        except Exception as e:
            logger.warning(f"LLM 提取失败: {e}")
            return truncated

    @staticmethod
    def _truncate(text: str, max_chars: int = 40000) -> str:
        """智能截断"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars]
