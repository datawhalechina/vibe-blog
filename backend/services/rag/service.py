"""
RAG Service — 统一入口

对标 DeepTutor src/services/rag/service.py，提供知识库初始化、检索、删除。
"""

import logging
import os
import shutil
from typing import Dict, List, Optional

from .types import Document, SearchResult
from .pipeline import RAGPipeline
from .components.chunkers.fixed import FixedSizeChunker
from .components.embedders.openai import OpenAIEmbedder
from .components.retrievers.dense import DenseRetriever

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 知识库检索服务"""

    def __init__(self, kb_base_dir: str = None):
        self.kb_base_dir = kb_base_dir or os.getenv(
            "RAG_KB_BASE_DIR", "data/knowledge_bases"
        )
        self._embedder = OpenAIEmbedder()
        self._retriever = DenseRetriever(kb_base_dir=self.kb_base_dir)
        self._pipeline = (
            RAGPipeline("default", self.kb_base_dir)
            .chunker(FixedSizeChunker(chunk_size=512, overlap=64))
            .embedder(self._embedder)
            .retriever(self._retriever)
        )

    async def initialize(self, kb_name: str, file_paths: List[str]) -> bool:
        """初始化知识库：读取文件 → 分块 → 向量化 → 索引"""
        documents = []
        for path in file_paths:
            if not os.path.exists(path):
                logger.warning(f"文件不存在: {path}")
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            documents.append(Document(content=content, file_path=path))

        if not documents:
            logger.warning(f"KB '{kb_name}' 无有效文档")
            return False

        return await self._pipeline.initialize(kb_name, documents)

    async def search(
        self,
        query: str,
        kb_name: str,
        mode: str = "dense",
        top_k: int = 5,
    ) -> SearchResult:
        """检索知识库"""
        # 生成查询向量
        embeddings = await self._embedder._embed_batch([query])
        query_embedding = embeddings[0] if embeddings else []

        if not query_embedding or all(v == 0.0 for v in query_embedding):
            return SearchResult(query=query, content="", mode=mode)

        self._retriever.top_k = top_k
        result = await self._pipeline.search(
            query_embedding, kb_name=kb_name, query=query
        )
        result.query = query
        return result

    async def delete(self, kb_name: str) -> bool:
        """删除知识库"""
        kb_dir = os.path.join(self.kb_base_dir, kb_name)
        if os.path.exists(kb_dir):
            shutil.rmtree(kb_dir)
            logger.info(f"KB '{kb_name}' 已删除")
            return True
        return False

    def list_knowledge_bases(self) -> List[str]:
        """列出所有知识库"""
        if not os.path.exists(self.kb_base_dir):
            return []
        return [
            d for d in os.listdir(self.kb_base_dir)
            if os.path.isdir(os.path.join(self.kb_base_dir, d))
        ]
