from services.blog_generator.schemas.state import SharedState
from services.blog_generator.blog_service import _normalize_research_result
from services.blog_generator.generator import BlogGenerator


def test_shared_state_preserves_skip_researcher_flag():
    assert "skip_researcher" in SharedState.__annotations__


def test_skipped_researcher_normalizes_empty_event_fields():
    background, concepts, stats, documents, results = _normalize_research_result({
        "background_knowledge": None,
        "key_concepts": None,
        "knowledge_source_stats": None,
        "document_knowledge": None,
        "search_results": None,
    })

    assert background == ""
    assert concepts == []
    assert stats == {}
    assert documents == []
    assert results == []


def test_skipped_researcher_provides_writer_safe_defaults():
    generator = object.__new__(BlogGenerator)
    state = {
        "skip_researcher": True,
        "background_knowledge": None,
        "key_concepts": None,
        "search_results": None,
        "distilled_sources": None,
        "knowledge_source_stats": None,
    }

    result = generator._researcher_node(state)

    assert result["background_knowledge"] == ""
    assert result["key_concepts"] == []
    assert result["search_results"] == []
    assert result["distilled_sources"] == []
    assert result["knowledge_source_stats"] == {}
