"""
引用收集器 — URL 去重 + 编号分配 + O(1) 查找
"""
import logging
from typing import Any, Dict, List, Optional

from .models import CitationMetadata

logger = logging.getLogger(__name__)


class CitationCollector:
    """收集和管理引用，贯穿博客生成全流程"""

    def __init__(self):
        self._citations: Dict[str, CitationMetadata] = {}
        self._citation_order: List[str] = []
        self._url_to_index: Dict[str, int] = {}

    def add_from_search_results(self, results: List[Dict[str, Any]]) -> int:
        """从搜索结果批量添加引用，返回新增数量"""
        added = 0
        for result in results:
            url = result.get("url", "")
            if not url:
                continue
            metadata = CitationMetadata.from_search_result(result)
            if url not in self._citations:
                self._citations[url] = metadata
                self._url_to_index[url] = len(self._citation_order)
                self._citation_order.append(url)
                added += 1
            else:
                existing = self._citations[url]
                if metadata.credibility_score > existing.credibility_score:
                    self._citations[url] = metadata
        if added:
            logger.info(f"引用收集: 新增 {added} 条，总计 {len(self._citations)} 条")
        return added

    def get_number(self, url: str) -> Optional[int]:
        """O(1) 获取引用编号（1-indexed）"""
        idx = self._url_to_index.get(url)
        return idx + 1 if idx is not None else None

    def get_all_as_list(self) -> List[Dict[str, Any]]:
        """导出为字典列表（供 state 存储）"""
        return [
            {"number": i + 1, **self._citations[url].model_dump()}
            for i, url in enumerate(self._citation_order)
        ]

    def to_markdown_references(self, style: str = "numbered") -> str:
        """生成 Markdown 参考文献段落"""
        if not self._citation_order:
            return ""
        lines = ["## References", ""]
        for i, url in enumerate(self._citation_order):
            meta = self._citations[url]
            lines.append(f"[{i + 1}] [{meta.title}]({meta.url})")
            if meta.domain:
                lines.append(f"  <!-- domain: {meta.domain} -->")
            lines.append("")
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._citations)
