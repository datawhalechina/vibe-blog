"""引用管理模块 — 结构化引用收集、去重、编号、多格式输出"""
from .models import CitationMetadata, ToolTrace
from .collector import CitationCollector
from .merger import merge_citations
from .manager import CitationManager

__all__ = ["CitationMetadata", "ToolTrace", "CitationCollector", "merge_citations", "CitationManager"]
