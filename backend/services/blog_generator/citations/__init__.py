"""引用管理模块 — 结构化引用收集、去重、编号、多格式输出"""
from .models import CitationMetadata
from .collector import CitationCollector
from .merger import merge_citations

__all__ = ["CitationMetadata", "CitationCollector", "merge_citations"]
