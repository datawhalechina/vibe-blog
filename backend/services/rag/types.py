"""
RAG 数据类型定义

对标 DeepTutor src/services/rag/types.py
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Chunk:
    """文档片段"""
    content: str
    chunk_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Document:
    """完整文档"""
    content: str
    file_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Chunk] = field(default_factory=list)


@dataclass
class SearchResult:
    """检索结果"""
    query: str
    answer: str = ""
    content: str = ""
    mode: str = "dense"
    provider: str = "default"
    chunks: List[Chunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
