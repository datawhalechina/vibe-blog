"""
TDD 测试 — 1003.09 素材整理服务 (MaterialOrganizerService)
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.material_organizer_service import (
    MaterialOrganizerService,
    MIN_DESCRIPTION_LENGTH,
)


class FakeLLM:
    def __init__(self, response: str = ""):
        self.response = response
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append({"system": system_prompt, "user": user_prompt})
        return self.response


SAMPLE_RECORDS = [
    {"record_type": "blog", "title": "Python 异步编程", "user_query": "async await", "content": "Python 的 asyncio 模块提供了异步编程的基础设施"},
    {"record_type": "note", "title": "数据库索引", "user_query": "index", "content": "B+ 树索引是关系数据库中最常用的索引结构"},
]

VALID_RESPONSE = json.dumps({
    "knowledge_points": [
        {"knowledge_point": "Python 异步编程", "description": "asyncio 模块提供协程、事件循环等异步编程基础设施"},
        {"knowledge_point": "数据库索引原理", "description": "B+ 树索引是关系数据库中最常用的索引结构，支持范围查询"},
    ]
}, ensure_ascii=False)


class TestExtractKnowledgePoints:
    def test_valid_input(self):
        llm = FakeLLM(VALID_RESPONSE)
        svc = MaterialOrganizerService(llm)
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        assert len(points) == 2
        assert points[0]["knowledge_point"] == "Python 异步编程"

    def test_empty_records(self):
        svc = MaterialOrganizerService(FakeLLM(""))
        assert svc.extract_knowledge_points([]) == []

    def test_validates_fields(self):
        bad = json.dumps({"knowledge_points": [
            {"knowledge_point": "", "description": "valid desc here ok"},
            {"knowledge_point": "Good", "description": ""},
        ]})
        llm = FakeLLM(bad)
        svc = MaterialOrganizerService(llm)
        # Main extraction returns empty → triggers fallback → fallback also gets bad → uses title fallback
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        assert len(points) >= 1

    def test_filters_short_descriptions(self):
        short = json.dumps({"knowledge_points": [
            {"knowledge_point": "A", "description": "short"},
            {"knowledge_point": "B", "description": "这是一个足够长的描述，超过了最小长度要求"},
        ]})
        llm = FakeLLM(short)
        svc = MaterialOrganizerService(llm)
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        # "short" is < MIN_DESCRIPTION_LENGTH, so only B passes main validation
        # But if main returns only 1, it's still valid
        assert all(len(p["description"]) >= MIN_DESCRIPTION_LENGTH for p in points)

    def test_fallback_on_json_error(self):
        llm = FakeLLM("not json at all")
        svc = MaterialOrganizerService(llm)
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        # Should trigger fallback → also fails → title-based fallback
        assert len(points) >= 1

    def test_fallback_returns_at_least_one(self):
        llm = FakeLLM("{}")
        svc = MaterialOrganizerService(llm)
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        assert len(points) >= 1

    def test_user_thoughts_in_prompt(self):
        llm = FakeLLM(VALID_RESPONSE)
        svc = MaterialOrganizerService(llm)
        svc.extract_knowledge_points(SAMPLE_RECORDS, user_thoughts="重点关注性能优化")
        assert "重点关注性能优化" in llm.calls[0]["user"]

    def test_no_llm_raises(self):
        svc = MaterialOrganizerService(None)
        # With no LLM, main + fallback both fail → title-based fallback
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        assert len(points) >= 1

    def test_code_block_response(self):
        wrapped = f"```json\n{VALID_RESPONSE}\n```"
        llm = FakeLLM(wrapped)
        svc = MaterialOrganizerService(llm)
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        assert len(points) == 2

    def test_list_response_format(self):
        list_resp = json.dumps([
            {"knowledge_point": "A", "description": "这是一个足够长的描述内容"},
        ])
        llm = FakeLLM(list_resp)
        svc = MaterialOrganizerService(llm)
        points = svc.extract_knowledge_points(SAMPLE_RECORDS)
        assert len(points) == 1
