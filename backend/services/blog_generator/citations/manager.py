"""
统一引用管理器 — 1003.03

对标 DeepTutor CitationManager，提供阶段化 ID 生成、工具追踪、引用验证。
增量增强现有 CitationCollector，不替换。
"""

import asyncio
import logging
import re
from typing import Dict, List

from .collector import CitationCollector
from .models import CitationMetadata, ToolTrace

logger = logging.getLogger(__name__)

# 引用 ID 正则
CITATION_PATTERN = re.compile(r"\[\[(PLAN-\d+|CIT-\d+-\d+)\]\]")


class CitationManager:
    """
    统一引用管理器

    在现有 CitationCollector 基础上增加：
    - 阶段化 ID 体系（PLAN-XX / CIT-X-XX）
    - 工具调用追踪（ToolTrace）
    - 引用验证与修复
    - 格式化输出
    """

    def __init__(self):
        self._collector = CitationCollector()
        self._tool_traces: Dict[str, ToolTrace] = {}
        self._citations: Dict[str, CitationMetadata] = {}
        self._stage_counters: Dict[str, int] = {}
        self._tool_counter = 0
        self._lock = asyncio.Lock()

    def generate_citation_id(self, stage: str = "research", block_id: str = "") -> str:
        """生成阶段化引用 ID"""
        if stage == "plan":
            key = "plan"
            self._stage_counters.setdefault(key, 0)
            self._stage_counters[key] += 1
            return f"PLAN-{self._stage_counters[key]:02d}"
        key = f"cit_{block_id}" if block_id else "cit_0"
        self._stage_counters.setdefault(key, 0)
        self._stage_counters[key] += 1
        bid = block_id or "0"
        return f"CIT-{bid}-{self._stage_counters[key]:02d}"

    def _next_tool_id(self) -> str:
        self._tool_counter += 1
        return f"tool_{self._tool_counter}"

    def add_citation(self, citation_id: str, tool_type: str,
                     query: str = "", raw_answer: str = "",
                     summary: str = "", search_result: dict = None) -> ToolTrace:
        """添加引用 — 同时记录工具追踪和搜索结果元数据"""
        trace = ToolTrace(
            tool_id=self._next_tool_id(),
            citation_id=citation_id,
            tool_type=tool_type,
            query=query, raw_answer=raw_answer, summary=summary,
        )
        self._tool_traces[citation_id] = trace
        if search_result:
            meta = CitationMetadata.from_search_result(search_result)
            self._citations[citation_id] = meta
            self._collector.add_from_search_results([search_result])
        return trace

    async def add_citation_async(self, *args, **kwargs) -> ToolTrace:
        async with self._lock:
            return self.add_citation(*args, **kwargs)

    def validate_references(self, text: str) -> Dict[str, List[str]]:
        """验证文本中的引用有效性"""
        found = CITATION_PATTERN.findall(text)
        valid = [c for c in found if c in self._tool_traces]
        invalid = [c for c in found if c not in self._tool_traces]
        return {"valid": valid, "invalid": invalid}

    def fix_invalid_references(self, text: str) -> str:
        """移除无效引用标记"""
        result = self.validate_references(text)
        fixed = text
        for cid in result["invalid"]:
            fixed = fixed.replace(f"[[{cid}]]", "")
        return fixed

    def format_citation(self, citation_id: str) -> str:
        trace = self._tool_traces.get(citation_id)
        if not trace:
            return ""
        meta = self._citations.get(citation_id)
        if meta:
            return f"[{citation_id}] {meta.title} — {meta.url}"
        return f"[{citation_id}] {trace.summary or trace.query or trace.tool_type}"

    def build_ref_number_map(self) -> Dict[str, int]:
        return {cid: i + 1 for i, cid in enumerate(sorted(self._tool_traces))}

    def format_references_section(self) -> str:
        if not self._tool_traces:
            return ""
        lines = ["## 参考文献\n"]
        for cid, num in self.build_ref_number_map().items():
            fmt = self.format_citation(cid)
            if fmt:
                lines.append(f"{num}. {fmt}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "tool_traces": {k: v.model_dump() for k, v in self._tool_traces.items()},
            "stage_counters": self._stage_counters.copy(),
            "tool_counter": self._tool_counter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CitationManager":
        mgr = cls()
        mgr._stage_counters = data.get("stage_counters", {})
        mgr._tool_counter = data.get("tool_counter", 0)
        for cid, td in data.get("tool_traces", {}).items():
            mgr._tool_traces[cid] = ToolTrace(**td)
        return mgr

    @property
    def citation_count(self) -> int:
        return len(self._tool_traces)

    @property
    def tool_types_summary(self) -> Dict[str, int]:
        s: Dict[str, int] = {}
        for t in self._tool_traces.values():
            s[t.tool_type] = s.get(t.tool_type, 0) + 1
        return s
