"""
引用数据模型 — 结构化引用元数据
融合 SourceCredibilityFilter 四维评分
"""
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


class CitationMetadata(BaseModel):
    """结构化引用元数据"""

    # 核心标识
    url: str
    title: str
    # 内容信息
    description: Optional[str] = None
    content_snippet: Optional[str] = None
    # 来源元数据
    domain: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    source_type: str = "web_search"  # web_search | document | local_material
    # 质量指标
    relevance_score: float = 0.0
    credibility_score: float = 0.0
    credibility_detail: Dict[str, Any] = Field(default_factory=dict)
    # 时间戳
    accessed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    # 扩展
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context: Any) -> None:
        if not self.domain and self.url:
            try:
                self.domain = urlparse(self.url).netloc or None
            except Exception:
                pass

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:12]

    @classmethod
    def from_search_result(cls, result: Dict[str, Any]) -> "CitationMetadata":
        """从 vibe-blog 搜索结果创建"""
        return cls(
            url=result.get("url", ""),
            title=result.get("title", "Untitled"),
            description=result.get("content", ""),
            content_snippet=(result.get("content", "") or "")[:500],
            source_type="web_search",
            relevance_score=result.get("relevance_score", 0.0),
            credibility_score=result.get("credibility_score", 0.0),
            credibility_detail=result.get("credibility_detail", {}),
            published_date=result.get("publish_date", ""),
            extra={"source": result.get("source", "")},
        )
