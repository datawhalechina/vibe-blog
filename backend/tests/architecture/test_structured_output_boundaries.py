import ast
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2]
CONSUMER_MODULES = [
    "services/blog_generator/blog_service.py",
    "services/blog_generator/agents/artist.py",
    "services/blog_generator/agents/coder.py",
    "services/blog_generator/agents/factcheck.py",
    "services/blog_generator/agents/humanizer.py",
    "services/blog_generator/agents/planner.py",
    "services/blog_generator/agents/questioner.py",
    "services/blog_generator/agents/researcher.py",
    "services/blog_generator/agents/reviewer.py",
    "services/blog_generator/agents/search_coordinator.py",
    "services/blog_generator/agents/summary_generator.py",
    "services/blog_generator/agents/thread_checker.py",
    "services/blog_generator/agents/voice_checker.py",
    "services/blog_generator/services/deep_research_engine.py",
    "services/blog_generator/services/goal_directed_extractor.py",
    "services/blog_generator/services/knowledge_gap_detector.py",
    "services/blog_generator/services/smart_search_service.py",
    "services/blog_generator/services/source_credibility_filter.py",
    "services/blog_generator/services/sub_query_engine.py",
]
FORBIDDEN_PARSER_NAMES = {
    "_extract_json",
    "_parse_extraction_json",
    "_parse_gaps",
    "_parse_response",
    "_parse_queries_response",
    "_repair_truncated_json",
}


@pytest.mark.parametrize("relative_path", CONSUMER_MODULES)
def test_llm_consumers_use_shared_structured_output_boundary(relative_path):
    path = BACKEND_ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    direct_loads = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "json"
        and node.func.attr == "loads"
    ]
    private_parsers = [
        (node.name, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in FORBIDDEN_PARSER_NAMES
    ]
    shared_calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "parse_structured_output"
    ]

    assert not direct_loads, f"direct json.loads calls at lines {direct_loads}"
    assert not private_parsers, f"private parsers remain: {private_parsers}"
    assert shared_calls, "module does not call parse_structured_output"
