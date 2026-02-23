"""
RAG Pipeline — 组合式管线

对标 DeepTutor src/services/rag/pipeline.py，Fluent API 串联组件。
"""

import logging
from typing import List, Optional

from .types import Chunk, Document
from .components.base import BaseComponent

logger = logging.getLogger(__name__)


class RAGPipeline:
    """组合式 RAG 管线"""

    def __init__(self, name: str = "default", kb_base_dir: str = "data/knowledge_bases"):
        self.name = name
        self.kb_base_dir = kb_base_dir
        self._chunker: Optional[BaseComponent] = None
        self._embedder: Optional[BaseComponent] = None
        self._retriever: Optional[BaseComponent] = None

    def chunker(self, c: BaseComponent) -> "RAGPipeline":
        self._chunker = c
        return self

    def embedder(self, e: BaseComponent) -> "RAGPipeline":
        self._embedder = e
        return self

    def retriever(self, r: BaseComponent) -> "RAGPipeline":
        self._retriever = r
        return self

    async def initialize(self, kb_name: str, documents: List[Document]) -> bool:
        """初始化知识库：分块 → 向量化 → 索引"""
        all_chunks: List[Chunk] = []

        for doc in documents:
            # 分块
            if self._chunker:
                chunks = await self._chunker.process(doc)
                doc.chunks = chunks
            else:
                doc.chunks = [Chunk(content=doc.content, metadata={"source": doc.file_path})]

            # 向量化
            if self._embedder:
                doc = await self._embedder.process(doc)

            all_chunks.extend(doc.chunks)

        # 索引
        if self._retriever and hasattr(self._retriever, "save_index"):
            await self._retriever.save_index(kb_name, all_chunks)

        logger.info(
            f"[RAGPipeline:{self.name}] 初始化完成: "
            f"{len(documents)} 文档, {len(all_chunks)} 片段"
        )
        return True

    async def search(self, query_embedding: list, kb_name: str, **kwargs):
        """检索知识库"""
        if not self._retriever:
            raise RuntimeError("Pipeline 未配置 retriever")
        return await self._retriever.process(
            query_embedding, kb_name=kb_name, **kwargs
        )
