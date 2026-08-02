import ast
from pathlib import Path

from services.blog_generator.schemas.state_contracts import NODE_STATE_CONTRACTS
from services.blog_generator.orchestrator.graph_builder import NODE_NAMES


BACKEND_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_ALIASES = {
    "outline": "Optional[OutlinePayload]",
    "sections": "SectionsPayload",
    "code_blocks": "CodeBlocksPayload",
    "images": "ImagesPayload",
    "question_results": "QuestionResultsPayload",
    "review_issues": "ReviewIssuesPayload",
    "instructional_analysis": "Optional[InstructionalAnalysisPayload]",
    "knowledge_gaps": "KnowledgeGapsPayload",
}


def _function(tree, name):
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def test_shared_state_uses_named_aliases_for_stable_payloads():
    tree = ast.parse(
        (BACKEND_ROOT / "services/blog_generator/schemas/state.py").read_text()
    )
    shared_state = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SharedState"
    )
    annotations = {
        node.target.id: ast.unparse(node.annotation)
        for node in shared_state.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

    assert {field: annotations[field] for field in EXPECTED_ALIASES} == EXPECTED_ALIASES


def test_contract_nodes_use_the_single_registration_boundary():
    builder_tree = ast.parse(
        (
            BACKEND_ROOT
            / "services/blog_generator/orchestrator/graph_builder.py"
        ).read_text()
    )
    assert set(NODE_STATE_CONTRACTS) <= set(NODE_NAMES)

    add_node = _function(builder_tree, "_add_node")
    called_functions = {
        call.func.id
        for call in ast.walk(add_node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }
    called_methods = {
        call.func.attr
        for call in ast.walk(add_node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }
    assert "wrap_node_state_contract" in called_functions
    assert "wrap_node" in called_methods
