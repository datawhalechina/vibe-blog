"""Tests for CreatorInsightService — 创作者洞察报告"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.creator_insight_service import BlogRecord, CreatorInsightService


class TestCreatorInsightService:
    """CreatorInsightService unit tests"""

    def setup_method(self):
        self.service = CreatorInsightService()

    # 1. empty records
    def test_empty_records(self):
        result = self.service.generate_insight([])
        assert result["total_blogs"] == 0
        assert result["total_words"] == 0
        assert result["avg_words"] == 0
        assert result["topic_distribution"] == []
        assert result["quality_trend"]["avg"] == 0.0
        assert result["quality_trend"]["trend"] == "insufficient_data"
        assert result["tag_cloud"] == []
        assert result["activity_streak"]["unique_days"] == 0
        assert result["activity_streak"]["total_records"] == 0
        assert len(result["suggestions"]) == 1
        assert "第一篇" in result["suggestions"][0]

    # 2. total stats
    def test_total_stats(self):
        records = [
            BlogRecord(title="A", topic="tech", created_at="2025-01-01", word_count=300),
            BlogRecord(title="B", topic="life", created_at="2025-01-02", word_count=700),
        ]
        result = self.service.generate_insight(records)
        assert result["total_blogs"] == 2
        assert result["total_words"] == 1000
        assert result["avg_words"] == 500

    # 3. topic distribution
    def test_topic_distribution(self):
        records = [
            BlogRecord(title="A", topic="tech", created_at="2025-01-01"),
            BlogRecord(title="B", topic="tech", created_at="2025-01-02"),
            BlogRecord(title="C", topic="life", created_at="2025-01-03"),
            BlogRecord(title="D", topic="ai", created_at="2025-01-04"),
        ]
        result = self.service.generate_insight(records)
        topics = {item["topic"]: item["count"] for item in result["topic_distribution"]}
        assert topics["tech"] == 2
        assert topics["life"] == 1
        assert topics["ai"] == 1
        # most_common ordering: tech first
        assert result["topic_distribution"][0]["topic"] == "tech"

    # 4. quality trend improving
    def test_quality_trend_improving(self):
        records = [
            BlogRecord(title=f"old{i}", topic="t", created_at=f"2025-01-0{i+1}", quality_score=3.0)
            for i in range(3)
        ] + [
            BlogRecord(title=f"new{i}", topic="t", created_at=f"2025-02-0{i+1}", quality_score=4.5)
            for i in range(3)
        ]
        result = self.service.generate_insight(records)
        assert result["quality_trend"]["trend"] == "improving"

    # 5. quality trend declining
    def test_quality_trend_declining(self):
        records = [
            BlogRecord(title=f"old{i}", topic="t", created_at=f"2025-01-0{i+1}", quality_score=4.5)
            for i in range(3)
        ] + [
            BlogRecord(title=f"new{i}", topic="t", created_at=f"2025-02-0{i+1}", quality_score=3.0)
            for i in range(3)
        ]
        result = self.service.generate_insight(records)
        assert result["quality_trend"]["trend"] == "declining"

    # 6. quality trend stable
    def test_quality_trend_stable(self):
        records = [
            BlogRecord(title=f"r{i}", topic="t", created_at=f"2025-01-0{i+1}", quality_score=4.0)
            for i in range(6)
        ]
        result = self.service.generate_insight(records)
        assert result["quality_trend"]["trend"] == "stable"

    # 7. quality trend insufficient data
    def test_quality_trend_insufficient(self):
        records = [
            BlogRecord(title="A", topic="t", created_at="2025-01-01", quality_score=4.0),
            BlogRecord(title="B", topic="t", created_at="2025-01-02", quality_score=3.5),
        ]
        result = self.service.generate_insight(records)
        assert result["quality_trend"]["trend"] == "insufficient_data"

    # 8. tag cloud
    def test_tag_cloud(self):
        records = [
            BlogRecord(title="A", topic="t", created_at="2025-01-01", tags=["python", "ai"]),
            BlogRecord(title="B", topic="t", created_at="2025-01-02", tags=["python", "web"]),
            BlogRecord(title="C", topic="t", created_at="2025-01-03", tags=["ai"]),
        ]
        result = self.service.generate_insight(records)
        tags = {item["tag"]: item["count"] for item in result["tag_cloud"]}
        assert tags["python"] == 2
        assert tags["ai"] == 2
        assert tags["web"] == 1

    # 9. activity streak
    def test_activity_streak(self):
        records = [
            BlogRecord(title="A", topic="t", created_at="2025-01-01"),
            BlogRecord(title="B", topic="t", created_at="2025-01-01"),  # same day
            BlogRecord(title="C", topic="t", created_at="2025-01-03"),
        ]
        result = self.service.generate_insight(records)
        assert result["activity_streak"]["unique_days"] == 2
        assert result["activity_streak"]["total_records"] == 3

    # 10. suggestions: diverse topics -> no diversity suggestion
    def test_suggestions_diverse_topics(self):
        records = [
            BlogRecord(title=f"r{i}", topic=f"topic{i}", created_at=f"2025-01-0{i+1}", word_count=800)
            for i in range(5)
        ]
        result = self.service.generate_insight(records)
        assert not any("多样性" in s for s in result["suggestions"])

    # 11. suggestions: few topics -> diversity suggestion
    def test_suggestions_few_topics(self):
        records = [
            BlogRecord(title=f"r{i}", topic="only_topic", created_at=f"2025-01-0{i+1}", word_count=800)
            for i in range(5)
        ]
        result = self.service.generate_insight(records)
        assert any("多样性" in s for s in result["suggestions"])

    # 12. suggestions: short articles -> length suggestion
    def test_suggestions_short_articles(self):
        records = [
            BlogRecord(title=f"r{i}", topic=f"topic{i}", created_at=f"2025-01-0{i+1}", word_count=200)
            for i in range(5)
        ]
        result = self.service.generate_insight(records)
        assert any("篇幅" in s for s in result["suggestions"])
