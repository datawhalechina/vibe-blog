"""
Dense Retriever — 基于向量余弦相似度的检索器

使用 numpy 计算余弦相似度，支持持久化索引到磁盘。
"""

import json
import logging
import os
from typing import Any, Dict, List

import numpy as np

from ..base import BaseComponent
from ...types import Chunk, SearchResult

logger = logging.getLogger(__name__)


class DenseRetriever(BaseComponent):
    """向量密集检索器"""
    name = "dense_retriever"

    def __init__(self, kb_base_dir: str = "data/knowledge_bases", top_k: int = 5):
        self.kb_base_dir = kb_base_dir
        self.top_k = top_k

    def _index_path(self, kb_name: str) -> str:
        return os.path.join(self.kb_base_dir, kb_name, "index")

    async def save_index(self, kb_name: str, chunks: List[Chunk]) -> None:
        """保存 chunk 向量索引到磁盘"""
        idx_dir = self._index_path(kb_name)
        os.makedirs(idx_dir, exist_ok=True)

        embeddings = []
        metadata_list = []
        for c in chunks:
            if c.embedding:
                embeddings.append(c.embedding)
                metadata_list.append({
                    "content": c.content,
                    "chunk_type": c.chunk_type,
                    "metadata": c.metadata,
                })

        if not embeddings:
            logger.warning(f"[DenseRetriever] KB '{kb_name}' 无 embedding 可索引")
            return

        np.save(os.path.join(idx_dir, "vectors.npy"), np.array(embeddings, dtype=np.float32))
        with open(os.path.join(idx_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, ensure_ascii=False)

        logger.info(f"[DenseRetriever] 索引保存: {len(embeddings)} 向量 → {idx_dir}")

    async def process(self, query_embedding: List[float], kb_name: str, **kwargs) -> SearchResult:
        """检索最相关的 top-k 片段"""
        idx_dir = self._index_path(kb_name)
        vectors_path = os.path.join(idx_dir, "vectors.npy")
        meta_path = os.path.join(idx_dir, "metadata.json")

        if not os.path.exists(vectors_path):
            return SearchResult(query="", content="", mode="dense")

        vectors = np.load(vectors_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata_list = json.load(f)

        # 余弦相似度
        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)
        v_norms = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)
        scores = v_norms @ q_norm

        top_k = min(self.top_k, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]

        result_chunks = []
        for i in top_indices:
            meta = metadata_list[i]
            result_chunks.append(Chunk(
                content=meta["content"],
                chunk_type=meta.get("chunk_type", "text"),
                metadata={**meta.get("metadata", {}), "score": float(scores[i])},
            ))

        content = "\n\n---\n\n".join(c.content for c in result_chunks)
        avg_score = float(np.mean([scores[i] for i in top_indices])) if top_indices.size else 0.0

        return SearchResult(
            query=kwargs.get("query", ""),
            content=content,
            mode="dense",
            provider="numpy",
            chunks=result_chunks,
            score=avg_score,
        )
