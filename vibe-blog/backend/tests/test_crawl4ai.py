"""
75.06 Crawl4AI 主动爬取 — 单元测试

覆盖：
- LocalMaterialStore: save / search / get_index / 增量检查
- BlogCrawler: 域名列表 / crawl_domain / 增量跳过
- SmartSearchService 集成: 本地优先查询
"""
import json
import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ========== Task 1: LocalMaterialStore ==========

class TestLocalMaterialStore:
    """测试本地素材库"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_store(self):
        from services.blog_generator.services.local_material_store import LocalMaterialStore
        return LocalMaterialStore(base_dir=self.tmpdir)

    def test_save_and_get_index(self):
        store = self._make_store()
        article = {
            "url": "https://anthropic.com/blog/claude-4",
            "domain": "anthropic.com",
            "title": "Introducing Claude 4",
            "content_md": "# Claude 4\n\nClaude 4 is here...",
            "summary": "Anthropic releases Claude 4 model",
            "keywords": ["claude", "anthropic", "llm"],
        }
        store.save(article)
        index = store.get_index()
        assert len(index) == 1
        assert index[0]["url"] == "https://anthropic.com/blog/claude-4"
        assert index[0]["title"] == "Introducing Claude 4"

    def test_save_dedup_by_url(self):
        store = self._make_store()
        article = {
            "url": "https://openai.com/blog/gpt5",
            "domain": "openai.com",
            "title": "GPT-5",
            "content_md": "# GPT-5\n\nContent here",
            "summary": "OpenAI GPT-5",
            "keywords": ["gpt5", "openai"],
        }
        store.save(article)
        store.save(article)  # 重复保存
        index = store.get_index()
        assert len(index) == 1

    def test_search_by_keyword(self):
        store = self._make_store()
        store.save({
            "url": "https://a.com/1",
            "domain": "a.com",
            "title": "Claude Agent Framework",
            "content_md": "Content about Claude agents",
            "summary": "A framework for building Claude agents",
            "keywords": ["claude", "agent"],
        })
        store.save({
            "url": "https://b.com/2",
            "domain": "b.com",
            "title": "Python Web Development",
            "content_md": "Content about Python web",
            "summary": "Building web apps with Python",
            "keywords": ["python", "web"],
        })
        results = store.search("claude agent")
        assert len(results) >= 1
        assert results[0]["url"] == "https://a.com/1"

    def test_search_empty_query(self):
        store = self._make_store()
        results = store.search("")
        assert results == []

    def test_search_no_match(self):
        store = self._make_store()
        store.save({
            "url": "https://a.com/1",
            "domain": "a.com",
            "title": "Rust Programming",
            "content_md": "Rust content",
            "summary": "Rust programming guide",
            "keywords": ["rust"],
        })
        results = store.search("quantum computing")
        assert len(results) == 0

    def test_has_url(self):
        store = self._make_store()
        store.save({
            "url": "https://a.com/1",
            "domain": "a.com",
            "title": "Test",
            "content_md": "Content",
            "summary": "Summary",
            "keywords": [],
        })
        assert store.has_url("https://a.com/1") is True
        assert store.has_url("https://b.com/2") is False

    def test_get_stats(self):
        store = self._make_store()
        store.save({
            "url": "https://a.com/1", "domain": "a.com",
            "title": "A1", "content_md": "C1", "summary": "S1", "keywords": [],
        })
        store.save({
            "url": "https://a.com/2", "domain": "a.com",
            "title": "A2", "content_md": "C2", "summary": "S2", "keywords": [],
        })
        store.save({
            "url": "https://b.com/1", "domain": "b.com",
            "title": "B1", "content_md": "C3", "summary": "S3", "keywords": [],
        })
        stats = store.get_stats()
        assert stats["total"] == 3
        assert stats["domains"]["a.com"] == 2
        assert stats["domains"]["b.com"] == 1


# ========== Task 2: BlogCrawler ==========

class TestBlogCrawler:
    """测试博客爬取器"""

    def test_high_quality_domains_defined(self):
        from services.blog_generator.services.blog_crawler import HIGH_QUALITY_BLOG_DOMAINS
        assert len(HIGH_QUALITY_BLOG_DOMAINS) >= 5
        assert "anthropic.com" in HIGH_QUALITY_BLOG_DOMAINS

    def test_crawler_init(self):
        from services.blog_generator.services.blog_crawler import BlogCrawler
        store = MagicMock()
        crawler = BlogCrawler(store=store)
        assert crawler.store is store

    def test_crawler_skip_existing_urls(self):
        from services.blog_generator.services.blog_crawler import BlogCrawler
        store = MagicMock()
        store.has_url.side_effect = lambda url: url == "https://a.com/old"
        crawler = BlogCrawler(store=store)
        urls = ["https://a.com/old", "https://a.com/new"]
        new_urls = crawler.filter_new_urls(urls)
        assert new_urls == ["https://a.com/new"]


# ========== Task 5: 配置项 ==========

class TestCrawl4AIConfig:
    """测试配置项"""

    def test_crawl4ai_config_exists(self):
        from config import Config
        assert hasattr(Config, 'CRAWL4AI_ENABLED')
        assert hasattr(Config, 'MATERIALS_DIR')
