import json
from types import SimpleNamespace

import pytest

from services.blog_generator.blog_service import BlogService


SCORES = {
    "factual_accuracy": 85,
    "completeness": 80,
    "coherence": 90,
    "relevance": 88,
    "citation_quality": 70,
    "writing_quality": 86,
}


class StaticLLM:
    def __init__(self, payload):
        self.payload = payload

    def chat(self, *args, **kwargs):
        return self.payload


def _service(payload):
    service = BlogService.__new__(BlogService)
    service.generator = SimpleNamespace(llm=StaticLLM(payload))
    return service


def _evaluation_payload(**overrides):
    payload = {
        "overall_score": 84,
        "grade": "B+",
        "scores": SCORES,
        "strengths": ["Clear structure"],
        "weaknesses": ["Few citations"],
        "suggestions": ["Add primary sources"],
        "summary": "A useful article.",
    }
    payload.update(overrides)
    return payload


def _assert_full_fallback(result):
    assert result["grade"] == "N/A"
    assert result["overall_score"] == 0
    assert result["scores"] == {
        "factual_accuracy": 0,
        "completeness": 0,
        "coherence": 0,
        "relevance": 0,
        "citation_quality": 0,
        "writing_quality": 0,
    }
    assert result["strengths"] == []
    assert result["weaknesses"] == []
    assert result["suggestions"] == []
    assert result["summary"] == "LLM 评估不可用，仅提供基础统计"


def test_missing_narrative_fields_receive_stable_defaults():
    payload = _evaluation_payload()
    payload.pop("strengths")
    payload.pop("weaknesses")
    payload.pop("suggestions")
    payload.pop("summary")

    result = _service(json.dumps(payload)).evaluate_article("# Article")

    assert result["overall_score"] == 84
    assert result["scores"] == SCORES
    assert result["strengths"] == []
    assert result["weaknesses"] == []
    assert result["suggestions"] == []
    assert result["summary"] == ""


def test_local_statistics_override_llm_supplied_values():
    content = (
        "Text [source](https://example.com)\n"
        "![diagram](image.png)\n"
        "```python\nprint(1)\n```"
    )
    payload = _evaluation_payload(
        word_count=999,
        citation_count=999,
        image_count=999,
        code_block_count=999,
    )

    result = _service(json.dumps(payload)).evaluate_article(content)

    assert result["word_count"] == len(content)
    assert result["citation_count"] == 1
    assert result["image_count"] == 1
    assert result["code_block_count"] == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"grade": "excellent"},
        {"overall_score": 101},
        {"scores": {**SCORES, "coherence": -1}},
        {"suggestions": "Add sources"},
    ],
)
def test_invalid_evaluation_contract_uses_full_fallback(overrides):
    result = _service(
        json.dumps(_evaluation_payload(**overrides))
    ).evaluate_article("Article")

    _assert_full_fallback(result)


def test_malformed_json_preserves_existing_fallback():
    result = _service('{"overall_score": 84').evaluate_article("Article")

    _assert_full_fallback(result)
