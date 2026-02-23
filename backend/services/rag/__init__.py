"""
RAG 知识库检索系统 — 1003.02

基于 DeepTutor RAG 架构迁移，提供组合式管线和多模式检索。
"""

from .types import Chunk, Document, SearchResult
from .service import RAGService
from .pipeline import RAGPipeline

__all__ = [
    "Chunk",
    "Document",
    "SearchResult",
    "RAGService",
    "RAGPipeline",
]
