"""
RAG → RetrieverRegistry 适配器

将 RAGService 适配为 vibe-blog RetrieverRegistry 的 BaseRetriever 接口。
"""

import asyncio
import logging
from typing import List, Optional

from ..service import RAGService

logger = logging.getLogger(__name__)


class RAGRetrieverAdapter:
    """将 RAGService 适配为 RetrieverRegistry 可注册的检索器"""

    name = "rag"

    def __init__(self, rag_service: RAGService, kb_name: str = "default"):
        self.rag_service = rag_service
        self.kb_name = kb_name

    def search(self, query: str, max_results: int = 10) -> List[dict]:
        """同步检索接口，适配 RetrieverRegistry"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        self.rag_service.search(query, self.kb_name, top_k=max_results),
                    ).result()
            else:
                result = asyncio.run(
                    self.rag_service.search(query, self.kb_name, top_k=max_results)
                )

            return [
                {
                    "title": f"KB: {c.metadata.get('source', 'unknown')}",
                    "body": c.content,
                    "source": "rag",
                    "score": c.metadata.get("score", 0.0),
                }
                for c in result.chunks
            ]
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")
            return []
