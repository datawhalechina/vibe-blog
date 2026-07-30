import json
from unittest.mock import MagicMock

from services.blog_generator.services.deep_research_engine import DeepResearchEngine
from services.blog_generator.services.goal_directed_extractor import GoalDirectedExtractor
from services.blog_generator.services.knowledge_gap_detector import KnowledgeGapDetector
from services.blog_generator.services.smart_search_service import SmartSearchService
from services.blog_generator.services.source_credibility_filter import SourceCredibilityFilter
from services.blog_generator.services.sub_query_engine import SubQueryEngine
from services.blog_generator.agents.researcher import ResearcherAgent


def test_deep_research_validation_failure_preserves_gap_fallback():
    llm = MagicMock()
    llm.chat.return_value = json.dumps(
        {"gaps": [{"topic": "Missing", "reason": "Why"}], "coverage_score": 30}
    )

    result = DeepResearchEngine(llm, search_service=None)._analyze_gaps(
        "Topic", "Knowledge", []
    )

    assert result == ([], 80)


def test_goal_extractor_validation_failure_retries_then_fails():
    llm = MagicMock()
    llm.chat.return_value = json.dumps({"rational": "Why", "evidence": "Proof"})

    result = GoalDirectedExtractor(llm_service=llm).extract("Content", "Goal")

    assert result.success is False
    assert llm.chat.call_count == 4


def test_knowledge_gap_validation_failure_preserves_empty_fallback():
    llm = MagicMock()
    llm.chat.return_value = json.dumps(
        [{"gap": "Missing detail", "refined_query": ["invalid"]}]
    )

    result = KnowledgeGapDetector(llm_service=llm).detect([], "Topic")

    assert result == []


def test_smart_search_validation_failure_preserves_rule_based_fallback():
    service = SmartSearchService.__new__(SmartSearchService)
    service.llm = MagicMock()
    service.llm.chat.return_value = json.dumps(
        {"sources": ["general"], "arxiv_query": [], "blog_query": "Topic"}
    )

    result = service._route_search_sources("Topic")

    assert result == {
        "sources": ["general"],
        "arxiv_query": "Topic",
        "blog_query": "Topic",
    }


def test_sub_query_validation_failure_preserves_three_level_fallback():
    llm = MagicMock()
    llm.chat.return_value = json.dumps(["first", "second", 7])
    engine = SubQueryEngine(llm_client=llm, search_service=None)

    result = engine.generate_sub_queries("Topic")

    assert result == engine._hardcoded_queries("Topic")
    assert llm.chat.call_count == 2


def test_research_summary_preserves_legacy_alternative_concept_key(monkeypatch):
    monkeypatch.setenv("RESEARCHER_CACHE_ENABLED", "false")
    llm = MagicMock()
    llm.chat.return_value = json.dumps(
        {"keyConcepts": [{"name": "Agent", "description": "Worker"}]}
    )

    result = ResearcherAgent(llm).summarize(
        "Topic",
        [{"title": "Source", "url": "https://example.com", "content": "Text"}],
        "beginner",
    )

    assert result == {
        "background_knowledge": "",
        "key_concepts": [{"name": "Agent", "description": "Worker"}],
        "top_references": [],
        "instructional_analysis": None,
    }


def test_researcher_run_normalizes_missing_instructional_analysis(monkeypatch):
    monkeypatch.setenv("RESEARCHER_CACHE_ENABLED", "false")
    monkeypatch.setenv("SMART_SEARCH_ENABLED", "false")
    researcher = ResearcherAgent(llm_client=None)
    researcher.search = MagicMock(
        return_value=[
            {"title": "Source", "url": "https://example.com", "content": "Text"}
        ]
    )
    researcher.summarize = MagicMock(
        return_value={
            "background_knowledge": "Background",
            "key_concepts": [],
            "top_references": [],
            "instructional_analysis": None,
        }
    )
    researcher.distill = MagicMock(return_value={})
    researcher.analyze_gaps = MagicMock(return_value={})

    result = researcher.run({"topic": "Topic", "target_audience": "beginner"})

    assert result["instructional_analysis"] == {}
    assert result["learning_objectives"] == []
    assert result["verbatim_data"] == []


def _credibility_results():
    return [
        {"title": f"Source {index}", "url": f"https://example.com/{index}"}
        for index in range(1, 7)
    ]


def test_source_credibility_filter_maps_and_sorts_valid_scores():
    llm = MagicMock()
    llm.chat.return_value = json.dumps(
        {
            "results": [
                {
                    "index": 2,
                    "authority": 9,
                    "freshness": 8,
                    "relevance": 9,
                    "depth": 8,
                    "total_score": 8.7,
                    "reason": "Strong",
                },
                {
                    "index": 1,
                    "authority": 7,
                    "freshness": 7,
                    "relevance": 7,
                    "depth": 7,
                    "total_score": 7.0,
                    "reason": "Useful",
                },
            ]
        }
    )

    result = SourceCredibilityFilter(llm).curate("Topic", _credibility_results())

    assert [item["title"] for item in result] == ["Source 2", "Source 1"]
    assert result[0]["credibility_score"] == 8.7
    assert result[0]["credibility_detail"]["reason"] == "Strong"


def test_source_credibility_filter_validation_failure_returns_original_results():
    llm = MagicMock()
    llm.chat.return_value = json.dumps(
        [
            {
                "index": 1,
                "authority": "invalid",
                "freshness": 8,
                "relevance": 9,
                "depth": 8,
                "total_score": 8.7,
                "reason": "Bad score",
            }
        ]
    )
    original = _credibility_results()

    result = SourceCredibilityFilter(llm).curate("Topic", original)

    assert result is original
