"""
OpenAI Embedding 组件

使用 OpenAI text-embedding API 生成向量。
"""

import logging
import os
from typing import List

from ..base import BaseComponent
from ...types import Chunk, Document

logger = logging.getLogger(__name__)


class OpenAIEmbedder(BaseComponent):
    """OpenAI Embedding 生成器"""
    name = "openai_embedder"

    def __init__(self, model: str = None, batch_size: int = 20):
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.batch_size = batch_size
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    async def process(self, document: Document, **kwargs) -> Document:
        """为文档的所有 chunk 生成 embedding"""
        if not document.chunks:
            return document

        texts = [c.content for c in document.chunks]
        embeddings = await self._embed_batch(texts)

        for chunk, emb in zip(document.chunks, embeddings):
            chunk.embedding = emb

        logger.info(f"[OpenAIEmbedder] 生成 {len(embeddings)} 个 embedding")
        return document

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        all_embeddings = []
        client = self._get_client()

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            try:
                response = client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                all_embeddings.extend([d.embedding for d in response.data])
            except Exception as e:
                logger.error(f"Embedding 生成失败: {e}")
                # fallback: 零向量
                all_embeddings.extend([[0.0] * 1536] * len(batch))

        return all_embeddings
