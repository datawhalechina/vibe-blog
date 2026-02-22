"""
TDD 测试 — 1003.03 统一引用管理 CitationManager
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.citations.models import ToolTrace
from services.blog_generator.citations.manager import CitationManager


class TestCitationIdGeneration:
    def test_plan_stage_ids(self):
        mgr = CitationManager()
        id1 = mgr.generate_citation_id(stage="plan")
        id2 = mgr.generate_citation_id(stage="plan")
        assert id1 == "PLAN-01"
        assert id2 == "PLAN-02"

    def test_research_stage_ids(self):
        mgr = CitationManager()
        id1 = mgr.generate_citation_id(stage="research", block_id="1")
        id2 = mgr.generate_citation_id(stage="research", block_id="1")
        id3 = mgr.generate_citation_id(stage="research", block_id="2")
        assert id1 == "CIT-1-01"
        assert id2 == "CIT-1-02"
        assert id3 == "CIT-2-01"

    def test_default_block_id(self):
        mgr = CitationManager()
        cid = mgr.generate_citation_id()
        assert cid == "CIT-0-01"


class TestAddCitation:
    def test_add_and_count(self):
        mgr = CitationManager()
        cid = mgr.generate_citation_id(stage="plan")
        trace = mgr.add_citation(cid, "web_search", query="test query")
        assert trace.citation_id == "PLAN-01"
        assert trace.tool_type == "web_search"
        assert mgr.citation_count == 1

    def test_add_with_search_result(self):
        mgr = CitationManager()
        cid = mgr.generate_citation_id(stage="research", block_id="1")
        mgr.add_citation(
            cid, "web_search",
            query="LLM",
            search_result={"url": "https://example.com", "title": "LLM Guide"},
        )
        assert mgr.citation_count == 1
        fmt = mgr.format_citation(cid)
        assert "LLM Guide" in fmt
        assert "example.com" in fmt

    def test_tool_types_summary(self):
        mgr = CitationManager()
        mgr.add_citation(mgr.generate_citation_id(stage="plan"), "web_search")
        mgr.add_citation(mgr.generate_citation_id(stage="plan"), "web_search")
        mgr.add_citation(mgr.generate_citation_id(stage="research"), "rag")
        assert mgr.tool_types_summary == {"web_search": 2, "rag": 1}


class TestValidateReferences:
    def test_valid_references(self):
        mgr = CitationManager()
        cid = mgr.generate_citation_id(stage="plan")
        mgr.add_citation(cid, "web_search")
        result = mgr.validate_references("See [[PLAN-01]] for details.")
        assert result["valid"] == ["PLAN-01"]
        assert result["invalid"] == []

    def test_invalid_references(self):
        mgr = CitationManager()
        result = mgr.validate_references("See [[CIT-9-99]] for details.")
        assert result["valid"] == []
        assert result["invalid"] == ["CIT-9-99"]

    def test_fix_invalid(self):
        mgr = CitationManager()
        cid = mgr.generate_citation_id(stage="plan")
        mgr.add_citation(cid, "web_search")
        text = "Valid [[PLAN-01]] and invalid [[CIT-9-99]] ref."
        fixed = mgr.fix_invalid_references(text)
        assert "[[PLAN-01]]" in fixed
        assert "[[CIT-9-99]]" not in fixed


class TestSerialization:
    def test_to_dict_and_from_dict(self):
        mgr = CitationManager()
        cid1 = mgr.generate_citation_id(stage="plan")
        mgr.add_citation(cid1, "web_search", query="test")
        cid2 = mgr.generate_citation_id(stage="research", block_id="1")
        mgr.add_citation(cid2, "rag", query="rag query")

        data = mgr.to_dict()
        restored = CitationManager.from_dict(data)
        assert restored.citation_count == 2
        assert "PLAN-01" in restored._tool_traces
        assert "CIT-1-01" in restored._tool_traces


class TestFormatOutput:
    def test_ref_number_map(self):
        mgr = CitationManager()
        mgr.add_citation(mgr.generate_citation_id(stage="plan"), "web_search")
        mgr.add_citation(mgr.generate_citation_id(stage="research", block_id="1"), "rag")
        ref_map = mgr.build_ref_number_map()
        assert len(ref_map) == 2
        # 编号从 1 开始
        assert all(v >= 1 for v in ref_map.values())

    def test_references_section(self):
        mgr = CitationManager()
        cid = mgr.generate_citation_id(stage="plan")
        mgr.add_citation(
            cid, "web_search", query="test",
            search_result={"url": "https://example.com", "title": "Example"},
        )
        section = mgr.format_references_section()
        assert "参考文献" in section
        assert "Example" in section

    def test_empty_references(self):
        mgr = CitationManager()
        assert mgr.format_references_section() == ""


class TestToolTrace:
    def test_auto_truncate(self):
        trace = ToolTrace(
            tool_id="t1", citation_id="CIT-0-01",
            tool_type="web_search", raw_answer="x" * 60000,
        )
        assert len(trace.raw_answer) < 60000
        assert trace.raw_answer.endswith("...[truncated]")
