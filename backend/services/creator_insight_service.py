"""
创作者洞察服务 -- 基于创作历史生成洞察报告

分析博客创作记录，生成主题分布、质量趋势、标签云、
活跃度统计和创作建议等洞察数据。
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class BlogRecord:
    title: str
    topic: str
    created_at: str
    word_count: int = 0
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)


class CreatorInsightService:
    """创作者洞察分析"""

    def generate_insight(self, records: List[BlogRecord]) -> dict:
        """基于创作历史生成洞察报告"""
        if not records:
            return self._empty_insight()
        return {
            "total_blogs": len(records),
            "total_words": sum(r.word_count for r in records),
            "avg_words": sum(r.word_count for r in records) // max(len(records), 1),
            "topic_distribution": self._analyze_topics(records),
            "quality_trend": self._analyze_quality(records),
            "tag_cloud": self._analyze_tags(records),
            "activity_streak": self._analyze_activity(records),
            "suggestions": self._generate_suggestions(records),
        }

    def _analyze_topics(self, records: List[BlogRecord]) -> List[dict]:
        counter = Counter(r.topic for r in records if r.topic)
        return [{"topic": t, "count": c} for t, c in counter.most_common(10)]

    def _analyze_quality(self, records: List[BlogRecord]) -> dict:
        scored = [r for r in records if r.quality_score > 0]
        if not scored:
            return {"avg": 0.0, "trend": "insufficient_data"}
        avg = sum(r.quality_score for r in scored) / len(scored)
        if len(scored) >= 3:
            recent = scored[-3:]
            older = scored[:-3] if len(scored) > 3 else scored[:1]
            recent_avg = sum(r.quality_score for r in recent) / len(recent)
            older_avg = sum(r.quality_score for r in older) / len(older)
            trend = "improving" if recent_avg > older_avg + 0.1 else (
                "declining" if recent_avg < older_avg - 0.1 else "stable"
            )
        else:
            trend = "insufficient_data"
        return {"avg": round(avg, 2), "trend": trend}

    def _analyze_tags(self, records: List[BlogRecord]) -> List[dict]:
        counter = Counter(tag for r in records for tag in r.tags)
        return [{"tag": t, "count": c} for t, c in counter.most_common(20)]

    def _analyze_activity(self, records: List[BlogRecord]) -> dict:
        dates = set()
        for r in records:
            try:
                dt = datetime.fromisoformat(r.created_at)
                dates.add(dt.date())
            except (ValueError, TypeError):
                pass
        return {
            "unique_days": len(dates),
            "total_records": len(records),
        }

    def _generate_suggestions(self, records: List[BlogRecord]) -> List[str]:
        suggestions = []
        topics = self._analyze_topics(records)
        if len(topics) <= 2:
            suggestions.append("尝试探索更多主题领域，丰富内容多样性")
        quality = self._analyze_quality(records)
        if quality["trend"] == "declining":
            suggestions.append("近期质量有所下降，建议增加研究深度")
        avg_words = sum(r.word_count for r in records) / max(len(records), 1)
        if avg_words < 500:
            suggestions.append("文章篇幅偏短，可考虑增加深度分析")
        if not suggestions:
            suggestions.append("保持当前创作节奏，质量稳定")
        return suggestions

    @staticmethod
    def _empty_insight() -> dict:
        return {
            "total_blogs": 0,
            "total_words": 0,
            "avg_words": 0,
            "topic_distribution": [],
            "quality_trend": {"avg": 0.0, "trend": "insufficient_data"},
            "tag_cloud": [],
            "activity_streak": {"unique_days": 0, "total_records": 0},
            "suggestions": ["开始创作第一篇博客吧！"],
        }
