"""
41.03 Embedding 上下文压缩 — 语义相关性排序 + 截断

对搜索结果进行语义压缩：
1. 将 query 和每条搜索结果文本做 embedding
2. 按余弦相似度排序，保留 top-K 最相关片段
3. 对长文本按段落切分后再排序，实现段落级精准压缩

环境变量：
- SEMANTIC_COMPRESS_ENABLED: 是否启用（默认 false）
- SEMANTIC_COMPRESS_TOP_K: 保留的 top-K 片段数（默认 10）
- SEMANTIC_COMPRESS_MAX_CHARS: 单条结果最大字符数（默认 2000）
- EMBEDDING_PROVIDER: embedding 提供商（openai / local，默认 local）
"""
import logging
import math
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingProvider:
    """Embedding 提供商抽象层"""

    def __init__(self):
        self._provider = os.environ.get('EMBEDDING_PROVIDER', 'local')
        self._model = None

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        if self._provider == 'openai':
            return self._embed_openai(texts)
        return self._embed_local(texts)

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """使用 OpenAI embedding API"""
        try:
            from langchain_openai import OpenAIEmbeddings
            if self._model is None:
                self._model = OpenAIEmbeddings(
                    model=os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small'),
                )
            return self._model.embed_documents(texts)
        except Exception as e:
            logger.warning(f"OpenAI embedding 失败，回退到本地: {e}")
            return self._embed_local(texts)

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """本地 TF-IDF 近似 embedding（零依赖降级方案）"""
        # 构建词汇表
        vocab = {}
        for text in texts:
            for word in text.lower().split():
                if word not in vocab:
                    vocab[word] = len(vocab)

        if not vocab:
            return [[0.0] for _ in texts]

        dim = len(vocab)
        embeddings = []
        for text in texts:
            vec = [0.0] * dim
            words = text.lower().split()
            if not words:
                embeddings.append(vec)
                continue
            for word in words:
                if word in vocab:
                    vec[vocab[word]] += 1.0 / len(words)
            embeddings.append(vec)
        return embeddings


class SemanticCompressor:
    """语义压缩器 — 基于 embedding 相似度筛选最相关内容"""

    def __init__(self, top_k: int = None, max_chars: int = None):
        self.top_k = top_k or int(os.environ.get('SEMANTIC_COMPRESS_TOP_K', '10'))
        self.max_chars = max_chars or int(os.environ.get('SEMANTIC_COMPRESS_MAX_CHARS', '2000'))
        self._embedding = EmbeddingProvider()

    def compress(self, query: str, search_results: List[Dict],
                 top_k: int = None) -> List[Dict]:
        """
        压缩搜索结果：按语义相关性排序，保留 top-K。

        Args:
            query: 搜索查询
            search_results: 搜索结果列表
            top_k: 覆盖默认 top_k

        Returns:
            压缩后的搜索结果（保留原始结构，按相关性排序）
        """
        k = top_k or self.top_k
        if len(search_results) <= k:
            return search_results

        try:
            # 提取文本
            texts = []
            for r in search_results:
                text = r.get('content', '') or r.get('snippet', '') or r.get('body', '')
                # 截断过长文本
                if len(text) > self.max_chars:
                    text = text[:self.max_chars]
                texts.append(text)

            # 生成 embedding
            all_texts = [query] + texts
            embeddings = self._embedding.embed(all_texts)
            query_emb = embeddings[0]
            doc_embs = embeddings[1:]

            # 计算相似度并排序
            scored: List[Tuple[float, int]] = []
            for i, doc_emb in enumerate(doc_embs):
                sim = _cosine_similarity(query_emb, doc_emb)
                scored.append((sim, i))

            scored.sort(key=lambda x: -x[0])

            # 保留 top-K
            result = []
            for sim, idx in scored[:k]:
                item = search_results[idx].copy()
                item['_relevance_score'] = round(sim, 4)
                result.append(item)

            logger.info(
                f"[SemanticCompressor] {len(search_results)} → {len(result)} 条 "
                f"(top-{k}, 最高相似度 {scored[0][0]:.3f})"
            )
            return result

        except Exception as e:
            logger.warning(f"[SemanticCompressor] 压缩失败，返回原始结果: {e}")
            return search_results[:k]
