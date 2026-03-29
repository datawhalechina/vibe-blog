"""
工具统一基类 — 迁移自 DeerFlow BaseTool 模式

定义搜索工具和爬虫工具的统一接口，
以及标准化的搜索结果数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    """统一搜索结果"""
    title: str = ""
    url: str = ""
    content: str = ""
    source: str = ""
    publish_date: str = ""
    source_type: str = "web"  # web | wechat | arxiv | scholar | local


@dataclass
class SearchResponse:
    """统一搜索响应"""
    success: bool = False
    results: List[SearchResult] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


class BaseSearchTool(ABC):
    """搜索工具统一基类"""

    name: str = ""
    group: str = "search"

    def configure(self, extra: Dict[str, Any]) -> None:
        """从 ToolConfig.extra 注入配置"""
        for k, v in extra.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @abstractmethod
    def is_available(self) -> bool:
        """检查工具是否可用（API Key 已配置等）"""
        ...

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """执行搜索"""
        ...


class BaseCrawlTool(ABC):
    """爬虫工具统一基类"""

    name: str = ""
    group: str = "crawl"

    def configure(self, extra: Dict[str, Any]) -> None:
        """从 ToolConfig.extra 注入配置"""
        for k, v in extra.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @abstractmethod
    def scrape(self, url: str) -> Optional[str]:
        """抓取 URL 内容，返回 Markdown 文本"""
        ...
