"""
41.17 可插拔检索器 — 统一检索器接口 + 注册表

统一所有搜索源为标准 Retriever 接口：
- BaseRetriever: 抽象基类，定义 search(query, max_results) 接口
- RetrieverRegistry: 注册表，按名称管理检索器实例
- SearchItem: 标准化搜索结果格式

环境变量：
- RETRIEVER_REGISTRY_ENABLED: 是否启用（默认 false）
- RETRIEVERS: 逗号分隔的检索器名称列表（默认 serper,sogou）
"""
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class SearchItem:
    """标准化搜索结果"""
    href: str = ""
    title: str = ""
    body: str = ""
    source: str = ""
    relevance_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "url": self.href,
            "title": self.title,
            "content": self.body,
            "source": self.source,
        }


class BaseRetriever(ABC):
    """检索器抽象基类"""

    name: str = "base"

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[SearchItem]:
        """执行搜索，返回标准化结果"""
        ...

    def is_available(self) -> bool:
        """检查检索器是否可用（API key 等）"""
        return True


class RetrieverRegistry:
    """检索器注册表 — 管理所有可用检索器"""

    _registry: Dict[str, Type[BaseRetriever]] = {}
    _instances: Dict[str, BaseRetriever] = {}

    @classmethod
    def register(cls, name: str, retriever_cls: Type[BaseRetriever]):
        """注册检索器类"""
        cls._registry[name] = retriever_cls
        logger.debug(f"[RetrieverRegistry] 注册检索器: {name}")

    @classmethod
    def get(cls, name: str) -> Optional[BaseRetriever]:
        """获取检索器实例（懒加载）"""
        if name in cls._instances:
            return cls._instances[name]
        if name not in cls._registry:
            logger.warning(f"[RetrieverRegistry] 未知检索器: {name}")
            return None
        try:
            instance = cls._registry[name]()
            if instance.is_available():
                cls._instances[name] = instance
                return instance
            logger.warning(f"[RetrieverRegistry] 检索器不可用: {name}")
            return None
        except Exception as e:
            logger.warning(f"[RetrieverRegistry] 检索器初始化失败 [{name}]: {e}")
            return None

    @classmethod
    def get_active_retrievers(cls) -> List[BaseRetriever]:
        """获取所有活跃的检索器"""
        names = os.environ.get('RETRIEVERS', 'serper,sogou').split(',')
        retrievers = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            r = cls.get(name)
            if r:
                retrievers.append(r)
        return retrievers

    @classmethod
    def list_registered(cls) -> List[str]:
        """列出所有已注册的检索器名称"""
        return list(cls._registry.keys())

    @classmethod
    def search_all(cls, query: str, max_results: int = 10) -> List[SearchItem]:
        """使用所有活跃检索器搜索并合并结果"""
        retrievers = cls.get_active_retrievers()
        if not retrievers:
            return []

        all_results: List[SearchItem] = []
        seen_urls = set()

        for retriever in retrievers:
            try:
                results = retriever.search(query, max_results=max_results)
                for item in results:
                    if item.href and item.href not in seen_urls:
                        seen_urls.add(item.href)
                        item.source = retriever.name
                        all_results.append(item)
            except Exception as e:
                logger.warning(f"[RetrieverRegistry] {retriever.name} 搜索失败: {e}")

        return all_results[:max_results]

    @classmethod
    def _reset(cls):
        """重置（测试用）"""
        cls._instances.clear()


# ========== 内置检索器适配器 ==========

class SerperRetriever(BaseRetriever):
    """Serper Google 搜索适配器"""
    name = "serper"

    def is_available(self) -> bool:
        return bool(os.environ.get('SERPER_API_KEY'))

    def search(self, query: str, max_results: int = 10) -> List[SearchItem]:
        from utils.rate_limiter import get_global_rate_limiter
        get_global_rate_limiter().wait_sync(domain='search_serper')
        # 委托给现有搜索服务
        from services.blog_generator.services.smart_search_service import get_smart_search_service
        service = get_smart_search_service()
        if not service:
            return []
        result = service._search_google(query, max_results)
        return [
            SearchItem(href=r.get('url', ''), title=r.get('title', ''),
                       body=r.get('content', '') or r.get('snippet', ''))
            for r in (result if isinstance(result, list) else result.get('results', []))
        ]


class SogouRetriever(BaseRetriever):
    """搜狗搜索适配器"""
    name = "sogou"

    def is_available(self) -> bool:
        return bool(os.environ.get('SOGOU_API_KEY') or os.environ.get('TENCENT_SECRET_ID'))

    def search(self, query: str, max_results: int = 10) -> List[SearchItem]:
        from utils.rate_limiter import get_global_rate_limiter
        get_global_rate_limiter().wait_sync(domain='search_sogou')
        from services.blog_generator.services.smart_search_service import get_smart_search_service
        service = get_smart_search_service()
        if not service:
            return []
        result = service._search_sogou(query, max_results)
        return [
            SearchItem(href=r.get('url', ''), title=r.get('title', ''),
                       body=r.get('content', '') or r.get('snippet', ''))
            for r in (result if isinstance(result, list) else result.get('results', []))
        ]


class ScholarRetriever(BaseRetriever):
    """Google Scholar search adapter for RetrieverRegistry"""
    name = "scholar"

    def is_available(self) -> bool:
        return bool(os.environ.get('SERPER_API_KEY'))

    def search(self, query: str, max_results: int = 10) -> List[SearchItem]:
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService()
        result = svc.search(query, max_results=max_results)
        if not result.get("success"):
            return []
        return [
            SearchItem(
                href=r.get("url", ""),
                title=r.get("title", ""),
                body=self._format_body(r),
                source="scholar",
            )
            for r in result.get("results", [])
        ]

    @staticmethod
    def _format_body(r: dict) -> str:
        parts = [r.get("snippet", "")]
        if r.get("publication_info"):
            parts.append(f"[{r['publication_info']}]")
        if r.get("year"):
            parts.append(f"({r['year']})")
        if r.get("cited_by"):
            parts.append(f"Cited: {r['cited_by']}")
        return " ".join(p for p in parts if p)


# 自动注册内置检索器
RetrieverRegistry.register("serper", SerperRetriever)
RetrieverRegistry.register("sogou", SogouRetriever)
RetrieverRegistry.register("scholar", ScholarRetriever)
