import json

import pytest

from services.blog_generator.agents.artist import ArtistAgent
from services.blog_generator.agents.coder import CoderAgent
from services.blog_generator.agents.factcheck import FactCheckAgent
from services.blog_generator.agents.humanizer import HumanizerAgent
from services.blog_generator.agents.planner import PlannerAgent
from services.blog_generator.agents.questioner import QuestionerAgent
from services.blog_generator.agents.researcher import ResearcherAgent
from services.blog_generator.agents.reviewer import ReviewerAgent
from services.blog_generator.agents.search_coordinator import SearchCoordinator
from services.blog_generator.agents.summary_generator import SummaryGeneratorAgent
from services.blog_generator.agents.thread_checker import ThreadCheckerAgent
from services.blog_generator.agents.voice_checker import VoiceCheckerAgent
from services.blog_generator.structured_output import StructuredOutputError


class StaticLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def chat(self, *args, **kwargs):
        self.calls += 1
        return self.payload


def test_artist_rejects_missing_required_caption():
    llm = StaticLLM(
        json.dumps({"render_method": "ai_image", "content": "image prompt"})
    )

    with pytest.raises(StructuredOutputError) as raised:
        ArtistAgent(llm).generate_image("comparison", "Compare", "Context")

    assert raised.value.kind == "validation"


def test_factcheck_validation_failure_uses_existing_error_report_fallback():
    llm = StaticLLM(json.dumps({"score": "invalid", "claims": [], "fixes": []}))
    state = {
        "sections": [{"id": "s1", "title": "One", "content": "Claim"}],
        "search_results": [],
    }

    result = FactCheckAgent(llm).run(state)

    assert "error" in result["factcheck_report"]


def test_humanizer_rejects_invalid_nested_score_type():
    llm = StaticLLM(
        json.dumps(
            {
                "score": {
                    "directness": 8,
                    "rhythm": 8,
                    "trust": 8,
                    "authenticity": 8,
                    "conciseness": 8,
                    "total": [],
                },
                "issues_summary": "none",
            }
        )
    )

    with pytest.raises(StructuredOutputError) as raised:
        HumanizerAgent(llm)._score_section("Natural text")

    assert raised.value.kind == "validation"


def test_reviewer_validation_failure_preserves_default_approval_fallback():
    llm = StaticLLM(
        json.dumps(
            {
                "score": 70,
                "approved": False,
                "issues": [
                    {
                        "section_id": "s1",
                        "issue_type": "logic",
                        "severity": "urgent",
                        "description": "Problem",
                        "suggestion": "Fix",
                    }
                ],
                "summary": "Needs work",
            }
        )
    )

    result = ReviewerAgent(llm).review("Document", {})

    assert result == {
        "score": 80,
        "approved": True,
        "issues": [],
        "summary": "审核完成",
    }


def test_summary_validation_failure_leaves_existing_state_unchanged():
    llm = StaticLLM(
        json.dumps(
            {
                "tldr": "Short",
                "seo_keywords": "not-a-list",
                "social_summary": "Social",
                "meta_description": "Meta",
            }
        )
    )
    state = {"final_markdown": "# Article", "outline": {"title": "Article"}}

    result = SummaryGeneratorAgent(llm).run(state)

    assert result["final_markdown"] == "# Article"
    assert "seo_keywords" not in result


def test_thread_checker_validation_failure_preserves_empty_issue_fallback():
    llm = StaticLLM(
        json.dumps(
            {
                "overall_coherence": 2,
                "issues": [
                    {
                        "check_type": "transition",
                        "severity": "urgent",
                        "section_id": "s1",
                        "description": "Problem",
                        "suggestion": "Fix",
                    }
                ],
                "summary": "Needs work",
            }
        )
    )
    state = {
        "sections": [
            {"id": "s1", "title": "One", "content": "First"},
            {"id": "s2", "title": "Two", "content": "Second"},
        ],
        "outline": {},
    }

    result = ThreadCheckerAgent(llm).run(state)

    assert result["thread_issues"] == []


def test_voice_checker_validation_failure_preserves_empty_issue_fallback():
    llm = StaticLLM(
        json.dumps(
            {
                "voice_profile": {
                    "target_tone": "clear",
                    "target_formality": "medium",
                    "target_person": "second",
                },
                "chapter_voice_map": [],
                "issues": [
                    {
                        "check_type": "tone_consistency",
                        "severity": "urgent",
                        "section_id": "s1",
                        "description": "Problem",
                        "suggestion": "Fix",
                    }
                ],
                "summary": "Needs work",
            }
        )
    )
    state = {
        "sections": [
            {"id": "s1", "title": "One", "content": "First"},
            {"id": "s2", "title": "Two", "content": "Second"},
        ]
    }

    result = VoiceCheckerAgent(llm).run(state)

    assert result["voice_issues"] == []


def test_coder_rejects_non_string_code_block():
    llm = StaticLLM(
        json.dumps(
            {"code_block": [], "output_block": "", "explanation": "Example"}
        )
    )

    with pytest.raises(StructuredOutputError) as raised:
        CoderAgent(llm).generate_code("Example", "Context")

    assert raised.value.kind == "validation"


def test_questioner_validation_failure_preserves_depth_fallback():
    llm = StaticLLM(
        json.dumps(
            {
                "is_detailed_enough": False,
                "depth_score": 20,
                "vague_points": [
                    {"location": "intro", "suggestion": "Add an example"}
                ],
            }
        )
    )

    result = QuestionerAgent(llm).check_depth("Content", {})

    assert result == {
        "is_detailed_enough": True,
        "depth_score": 80,
        "vague_points": [],
    }


def test_search_coordinator_validation_failure_preserves_empty_gap_fallback():
    llm = StaticLLM(
        json.dumps(
            {
                "gaps": [
                    {
                        "gap_type": "unknown",
                        "description": "Missing detail",
                        "suggested_query": "topic detail",
                    }
                ]
            }
        )
    )

    result = SearchCoordinator(llm, search_service=None).detect_knowledge_gaps(
        "Content", "Knowledge"
    )

    assert result == []


def test_researcher_validation_failure_preserves_default_queries(monkeypatch):
    monkeypatch.setenv("RESEARCHER_CACHE_ENABLED", "false")
    llm = StaticLLM(json.dumps(["topic overview", 7]))

    result = ResearcherAgent(llm).generate_search_queries("topic", "beginner")

    assert result == [
        "topic 教程 tutorial",
        "topic 最佳实践 best practices",
        "topic 常见问题 FAQ",
    ]


def test_planner_uses_explicit_repair_for_nested_truncated_output():
    llm = StaticLLM(
        'thinking first\n{"title":"T","sections":[{"title":"One",'
        '"subsections":[{"title":"Nested"'
    )

    result = PlannerAgent(llm).generate_outline(
        topic="Topic",
        article_type="tutorial",
        target_audience="beginner",
    )

    assert result["title"] == "T"
    assert result["sections"][0]["subsections"] == [{"title": "Nested"}]
