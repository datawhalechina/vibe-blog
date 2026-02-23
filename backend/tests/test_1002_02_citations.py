"""引用管理模块单元测试 — CitationMetadata + CitationCollector + merge_citations"""
import pytest
from services.blog_generator.citations.models import CitationMetadata
from services.blog_generator.citations.collector import CitationCollector
from services.blog_generator.citations.merger import merge_citations


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_search_results():
    """模拟 vibe-blog 搜索结果"""
    return [
        {
            "title": "Understanding Transformers",
            "url": "https://arxiv.org/abs/2401.12345",
            "content": "A comprehensive guide to transformer architecture...",
            "source": "arXiv",
            "publish_date": "2026-01-15",
            "relevance_score": 0.92,
            "credibility_score": 8.6,
            "credibility_detail": {
                "authority": 9, "freshness": 8, "relevance": 9, "depth": 8
            },
        },
        {
            "title": "Transformer Best Practices",
            "url": "https://huggingface.co/blog/transformers-guide",
            "content": "Best practices for using transformers in production...",
            "source": "Hugging Face",
            "publish_date": "2026-02-01",
            "relevance_score": 0.85,
        },
        {
            "title": "Duplicate Entry",
            "url": "https://arxiv.org/abs/2401.12345",  # 重复 URL
            "content": "Same paper, different title",
            "relevance_score": 0.70,
        },
    ]


@pytest.fixture
def empty_collector():
    return CitationCollector()


@pytest.fixture
def populated_collector(sample_search_results):
    collector = CitationCollector()
    collector.add_from_search_results(sample_search_results)
    return collector


# ── CitationMetadata Tests ────────────────────────────────────────────

class TestCitationMetadata:
    def test_from_search_result(self, sample_search_results):
        meta = CitationMetadata.from_search_result(sample_search_results[0])
        assert meta.url == "https://arxiv.org/abs/2401.12345"
        assert meta.title == "Understanding Transformers"
        assert meta.domain == "arxiv.org"
        assert meta.credibility_score == 8.6
        assert meta.credibility_detail["authority"] == 9

    def test_id_deterministic(self):
        m1 = CitationMetadata(url="https://example.com", title="A")
        m2 = CitationMetadata(url="https://example.com", title="B")
        assert m1.id == m2.id  # 同 URL → 同 ID

    def test_id_differs_for_different_urls(self):
        m1 = CitationMetadata(url="https://a.com", title="A")
        m2 = CitationMetadata(url="https://b.com", title="B")
        assert m1.id != m2.id

    def test_domain_auto_extract(self):
        meta = CitationMetadata(url="https://blog.example.com/post", title="T")
        assert meta.domain == "blog.example.com"

    def test_domain_empty_url(self):
        meta = CitationMetadata(url="", title="T")
        assert meta.domain is None or meta.domain == ""

    def test_from_search_result_missing_fields(self):
        """搜索结果缺少可选字段时不报错"""
        meta = CitationMetadata.from_search_result({"url": "https://x.com", "title": "X"})
        assert meta.url == "https://x.com"
        assert meta.credibility_score == 0.0

    def test_from_search_result_empty_url(self):
        meta = CitationMetadata.from_search_result({})
        assert meta.url == ""
        assert meta.title == "Untitled"


# ── CitationCollector Tests ───────────────────────────────────────────

class TestCitationCollector:
    def test_add_dedup(self, empty_collector, sample_search_results):
        added = empty_collector.add_from_search_results(sample_search_results)
        assert added == 2  # 3 条输入，1 条重复 URL
        assert empty_collector.count == 2

    def test_add_empty(self, empty_collector):
        added = empty_collector.add_from_search_results([])
        assert added == 0
        assert empty_collector.count == 0

    def test_add_skips_no_url(self, empty_collector):
        added = empty_collector.add_from_search_results([{"title": "No URL"}])
        assert added == 0

    def test_high_score_overwrites(self, empty_collector):
        """重复 URL 时高分覆盖低分"""
        empty_collector.add_from_search_results([
            {"url": "https://a.com", "title": "Low", "credibility_score": 3.0},
        ])
        empty_collector.add_from_search_results([
            {"url": "https://a.com", "title": "High", "credibility_score": 9.0},
        ])
        assert empty_collector.count == 1
        items = empty_collector.get_all_as_list()
        assert items[0]["credibility_score"] == 9.0

    def test_numbering(self, populated_collector):
        assert populated_collector.get_number("https://arxiv.org/abs/2401.12345") == 1
        assert populated_collector.get_number("https://huggingface.co/blog/transformers-guide") == 2
        assert populated_collector.get_number("https://nonexistent.com") is None

    def test_markdown_output(self, populated_collector):
        md = populated_collector.to_markdown_references()
        assert "## References" in md
        assert "[1]" in md
        assert "[2]" in md
        assert "arxiv.org" in md

    def test_markdown_empty(self, empty_collector):
        assert empty_collector.to_markdown_references() == ""

    def test_export_list(self, populated_collector):
        items = populated_collector.get_all_as_list()
        assert len(items) == 2
        assert items[0]["number"] == 1
        assert items[1]["number"] == 2
        assert "url" in items[0]
        assert "title" in items[0]


# ── merge_citations Tests ────────────────────────────────────────────

class TestMergeCitations:
    def test_merge_dedup(self):
        existing = [{"url": "https://a.com", "title": "A", "credibility_score": 5}]
        new = [
            {"url": "https://b.com", "title": "B", "credibility_score": 7},
            {"url": "https://a.com", "title": "A v2", "credibility_score": 8},
        ]
        merged = merge_citations(existing, new)
        assert len(merged) == 2
        a_item = [m for m in merged if m["url"] == "https://a.com"][0]
        assert a_item["credibility_score"] == 8  # 高分覆盖

    def test_merge_empty(self):
        assert merge_citations([], []) == []
        assert merge_citations([{"url": "x"}], []) == [{"url": "x"}]
        assert len(merge_citations([], [{"url": "y"}])) == 1

    def test_merge_no_url_skipped(self):
        merged = merge_citations([], [{"title": "no url"}, {"url": "https://a.com"}])
        assert len(merged) == 1

    def test_merge_preserves_order(self):
        existing = [
            {"url": "https://a.com", "credibility_score": 1},
            {"url": "https://b.com", "credibility_score": 2},
        ]
        new = [{"url": "https://c.com", "credibility_score": 3}]
        merged = merge_citations(existing, new)
        urls = [m["url"] for m in merged]
        assert urls == ["https://a.com", "https://b.com", "https://c.com"]
