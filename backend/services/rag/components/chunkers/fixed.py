"""
固定大小分块器

对标 DeepTutor 的 FixedChunker，按固定字符数分块，带重叠。
"""

from typing import List

from ..base import BaseComponent
from ...types import Chunk, Document


class FixedSizeChunker(BaseComponent):
    """固定大小分块器"""
    name = "fixed_chunker"

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def process(self, document: Document, **kwargs) -> List[Chunk]:
        text = document.content
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [Chunk(
                content=text,
                metadata={"source": document.file_path, "chunk_index": 0},
            )]

        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            chunks.append(Chunk(
                content=chunk_text,
                metadata={"source": document.file_path, "chunk_index": idx},
            ))
            start = end - self.overlap
            idx += 1

        return chunks
