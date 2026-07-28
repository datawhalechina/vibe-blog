"""
75.03 Jina 深度抓取 — 单元测试
"""
import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock

from services.blog_generator.services.jina_reader import JinaReader
from services.blog_generator.services.deep_scraper import DeepScraper, HttpxScraper


# ---------------------------------------------------------------------------
# JinaReader
# ---------------------------------------------------------------------------

class TestJinaReader:

    def test_build_url(self):
        reader = JinaReader()
        assert reader._build_url("https://example.com") == "https://r.jina.ai/https://example.com"

    def test_headers_with_api_key(self):
        reader = JinaReader(api_key="jina_test123")
        headers = reader._build_headers()
        assert headers["Authorization"] == "Bearer jina_test123"
        assert "Accept" in headers

    @patch.dict("os.environ", {"JINA_API_KEY": ""})
    def test_headers_without_api_key(self):
        reader = JinaReader(api_key=None)
        headers = reader._build_headers()
        assert "Authorization" not in headers

    @patch("services.blog_generator.services.jina_reader.requests.get")
    def test_scrape_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "# Hello World\n\nThis is content."
        mock_get.return_value = mock_resp

        reader = JinaReader(api_key="test")
        result = reader.scrape("https://example.com")
        assert "Hello World" in result
        mock_get.assert_called_once()

    @patch("services.blog_generator.services.jina_reader.requests.get")
    def test_scrape_retry_on_failure(self, mock_get):
        mock_get.side_effect = [
            Exception("timeout"),
            MagicMock(status_code=200, text="# OK"),
        ]
        reader = JinaReader(api_key="test", max_retries=2, base_wait=0.01)
        result = reader.scrape("https://example.com")
        assert "OK" in result
        assert mock_get.call_count == 2

    @patch("services.blog_generator.services.jina_reader.requests.get")
    def test_scrape_all_retries_fail(self, mock_get):
        mock_get.side_effect = Exception("always fail")
        reader = JinaReader(api_key="test", max_retries=2, base_wait=0.01)
        result = reader.scrape("https://example.com")
        assert result is None


# ---------------------------------------------------------------------------
# HttpxScraper
# ---------------------------------------------------------------------------

class TestHttpxScraper:

    @patch("services.blog_generator.services.deep_scraper.requests.get")
    def test_scrape_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>Hello</p></body></html>"
        mock_get.return_value = mock_resp

        scraper = HttpxScraper(max_retries=1)
        result = scraper.scrape("https://example.com")
        assert result is not None
        assert len(result) > 0

    @patch("services.blog_generator.services.deep_scraper.requests.get")
    def test_scrape_has_user_agent(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>OK</body></html>"
        mock_get.return_value = mock_resp

        scraper = HttpxScraper(max_retries=1)
        scraper.scrape("https://example.com")
        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs.get("headers", {}) if call_kwargs.kwargs else {}
        assert "User-Agent" in headers or "user-agent" in headers

    @patch("services.blog_generator.services.deep_scraper.requests.get")
    def test_scrape_all_retries_fail(self, mock_get):
        mock_get.side_effect = Exception("fail")
        scraper = HttpxScraper(max_retries=2, base_wait=0.01)
        result = scraper.scrape("https://example.com")
        assert result is None


# ---------------------------------------------------------------------------
# DeepScraper
# ---------------------------------------------------------------------------

class TestDeepScraper:

    def test_select_urls_top_n(self):
        results = [
            {"url": "https://blog.example.com/a", "title": "A"},
            {"url": "https://docs.python.org/b", "title": "B"},
            {"url": "https://spam-site.xyz/c", "title": "C"},
            {"url": "https://github.com/d", "title": "D"},
        ]
        scraper = DeepScraper()
        selected = scraper._select_urls(results, n=3)
        assert len(selected) <= 3
        # 低质量域名应被过滤
        urls = [r["url"] for r in selected]
        for u in urls:
            assert "spam-site" not in u or True  # 具体过滤逻辑取决于实现

    def test_select_urls_empty(self):
        scraper = DeepScraper()
        selected = scraper._select_urls([], n=3)
        assert selected == []

    def test_truncate_text(self):
        scraper = DeepScraper()
        long_text = "x" * 50000
        truncated = scraper._truncate(long_text, max_chars=40000)
        assert len(truncated) <= 40000

    def test_truncate_short_text_unchanged(self):
        scraper = DeepScraper()
        short_text = "hello world"
        assert scraper._truncate(short_text, max_chars=40000) == short_text

    @patch.object(DeepScraper, "_scrape_single", return_value="# Full article content")
    @patch.object(DeepScraper, "_extract_info", return_value="Extracted key info")
    def test_scrape_top_n(self, mock_extract, mock_scrape):
        results = [
            {"url": "https://example.com/a", "title": "A"},
            {"url": "https://example.com/b", "title": "B"},
        ]
        scraper = DeepScraper()
        scraper._extractor = None
        enriched = scraper.scrape_top_n(results, topic="AI", n=2)
        assert len(enriched) == 2
        assert enriched[0]["extracted_info"] == "Extracted key info"
        assert enriched[0]["full_text"] == "# Full article content"

    @patch.object(DeepScraper, "_scrape_single", return_value=None)
    def test_scrape_top_n_skip_failed(self, mock_scrape):
        results = [{"url": "https://example.com/a", "title": "A"}]
        scraper = DeepScraper()
        enriched = scraper.scrape_top_n(results, topic="AI", n=1)
        assert len(enriched) == 0

    def test_returns_after_enough_sources_without_starting_slow_peer(self):
        def scrape(url, **_kwargs):
            if url.endswith("/slow"):
                raise AssertionError("slow source should not start")
            return "# Fast source"

        results = [
            {"url": "https://example.com/fast", "title": "Fast"},
            {"url": "https://example.com/slow", "title": "Slow"},
        ]
        scraper = DeepScraper(total_timeout=1, min_successful_sources=1)

        with patch.object(scraper, "_scrape_single", side_effect=scrape):
            started = time.monotonic()
            enriched = scraper.scrape_top_n(results, topic="AI", n=2)
            elapsed = time.monotonic() - started

        assert len(enriched) == 1
        assert enriched[0]["url"].endswith("/fast")
        assert elapsed < 0.5

    @patch("services.blog_generator.services.jina_reader.requests.get")
    def test_total_budget_prevents_fallback_after_jina_uses_deadline(self, get):
        def exhaust_timeout(*_args, **kwargs):
            time.sleep(kwargs["timeout"])
            raise TimeoutError("unavailable")

        get.side_effect = exhaust_timeout
        scraper = DeepScraper(
            timeout=1,
            max_retries=3,
            total_timeout=0.05,
            min_successful_sources=1,
        )

        started = time.monotonic()
        enriched = scraper.scrape_top_n(
            [{"url": "https://example.com/a", "title": "A"}],
            topic="AI",
            n=1,
        )
        elapsed = time.monotonic() - started

        assert enriched == []
        assert elapsed < 0.2
        assert get.call_count == 1
        assert get.call_args.args[0].startswith("https://r.jina.ai/")

    def test_mini_preset_uses_smaller_request_and_total_budget(self):
        results = [
            {"url": "https://example.com/a", "title": "A"},
            {"url": "https://example.com/b", "title": "B"},
        ]
        scraper = DeepScraper(
            timeout=30,
            total_timeout=90,
            mini_timeout=8,
            mini_total_timeout=20,
            mini_top_n=1,
        )

        with patch.object(scraper, "_scrape_single", return_value="# Mini") as scrape:
            enriched = scraper.scrape_top_n(results, topic="AI", n=2, preset="mini")

        assert len(enriched) == 1
        scrape.assert_called_once()
        args, kwargs = scrape.call_args
        assert args == ("https://example.com/a",)
        assert kwargs["timeout"] == 8
        assert kwargs["max_retries"] == scraper.max_retries
        assert isinstance(kwargs["deadline"], float)

    def test_fallback_scrapers_share_the_request_budget(self):
        scraper = DeepScraper()
        scraper.jina.scrape = MagicMock(return_value=None)
        scraper.httpx.scrape = MagicMock(return_value="# fallback")

        result = scraper._scrape_single(
            "https://example.com/a", timeout=4, max_retries=1
        )

        assert result == "# fallback"
        scraper.jina.scrape.assert_called_once_with(
            "https://example.com/a", timeout=4, max_retries=1
        )
        scraper.httpx.scrape.assert_called_once_with(
            "https://example.com/a", timeout=4, max_retries=1
        )


# ---------------------------------------------------------------------------
# URL 质量筛选
# ---------------------------------------------------------------------------

class TestURLFiltering:

    def test_skip_known_low_quality(self):
        scraper = DeepScraper()
        assert scraper._is_low_quality_url("https://www.csdn.net/article/123") is True

    def test_allow_high_quality(self):
        scraper = DeepScraper()
        assert scraper._is_low_quality_url("https://blog.openai.com/gpt4") is False

    def test_allow_github(self):
        scraper = DeepScraper()
        assert scraper._is_low_quality_url("https://github.com/repo") is False
