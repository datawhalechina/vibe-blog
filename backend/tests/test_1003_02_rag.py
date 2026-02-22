"""
TDD 测试 — 1003.02 RAG 知识库检索系统
"""

import json
import os
import sys
import tempfile
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.rag.types import Chunk, Document, SearchResult
from services.rag.components.chunkers.fixed import FixedSizeChunker
from services.rag.components.retrievers.dense import DenseRetriever
from services.rag.pipeline import RAGPipeline


# --- 数据类型测试 ---
class TestTypes:
    def test_chunk_creation(self):
        chunk = Chunk(content="hello", chunk_type="text")
        assert chunk.content == "hello"
        assert chunk.metadata == {}
        assert chunk.embedding is None

    def test_chunk_with_embedding(self):
        chunk = Chunk(content="hello", embedding=[0.1, 0.2, 0.3])
        assert len(chunk.embedding) == 3

    def test_document_creation(self):
        doc = Document(content="full text", file_path="/tmp/test.txt")
        assert doc.chunks == []

    def test_search_result(self):
        sr = SearchResult(query="test", content="result", score=0.95)
        assert sr.mode == "dense"
        assert sr.score == 0.95


# --- FixedSizeChunker 测试 ---
class TestFixedSizeChunker:
    @pytest.mark.asyncio
    async def test_short_document_no_split(self):
        chunker = FixedSizeChunker(chunk_size=100, overlap=10)
        doc = Document(content="Short text")
        chunks = await chunker.process(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text"

    @pytest.mark.asyncio
    async def test_long_document_splits(self):
        chunker = FixedSizeChunker(chunk_size=10, overlap=2)
        doc = Document(content="A" * 25, file_path="test.txt")
        chunks = await chunker.process(doc)
        assert len(chunks) > 1
        # 每个 chunk 不超过 chunk_size
        for c in chunks:
            assert len(c.content) <= 10

    @pytest.mark.asyncio
    async def test_empty_document(self):
        chunker = FixedSizeChunker()
        doc = Document(content="")
        chunks = await chunker.process(doc)
        assert chunks == []


# --- DenseRetriever 测试 ---
class TestDenseRetriever:
    @pytest.mark.asyncio
    async def test_save_and_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = DenseRetriever(kb_base_dir=tmpdir, top_k=2)

            # 创建带 embedding 的 chunks
            chunks = [
                Chunk(content="Python is a programming language", embedding=[1.0, 0.0, 0.0]),
                Chunk(content="Java is also a programming language", embedding=[0.9, 0.1, 0.0]),
                Chunk(content="Cooking recipes are fun", embedding=[0.0, 0.0, 1.0]),
            ]

            await retriever.save_index("test_kb", chunks)

            # 搜索 — 查询向量接近 Python/Java
            result = await retriever.process(
                [1.0, 0.0, 0.0], kb_name="test_kb", query="programming"
            )
            assert len(result.chunks) == 2
            assert "Python" in result.chunks[0].content or "Java" in result.chunks[0].content

    @pytest.mark.asyncio
    async def test_missing_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = DenseRetriever(kb_base_dir=tmpdir)
            result = await retriever.process([1.0, 0.0], kb_name="nonexistent")
            assert result.content == ""


# --- RAGPipeline 测试 ---
class TestRAGPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_initialize(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chunker = FixedSizeChunker(chunk_size=50, overlap=5)
            retriever = DenseRetriever(kb_base_dir=tmpdir)

            # 跳过 embedder（测试中不调用 OpenAI）
            pipeline = (
                RAGPipeline("test", tmpdir)
                .chunker(chunker)
                .retriever(retriever)
            )

            docs = [Document(content="A" * 100, file_path="test.txt")]
            result = await pipeline.initialize("test_kb", docs)
            assert result is True

            # 验证 chunks 被创建
            assert len(docs[0].chunks) > 1
