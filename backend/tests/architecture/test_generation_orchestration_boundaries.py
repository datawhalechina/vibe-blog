import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE_ROOT = BACKEND_ROOT / "services" / "blog_generator" / "lifecycle"
ORCHESTRATOR_ROOT = BACKEND_ROOT / "services" / "blog_generator" / "orchestrator"


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def _method_calls(path: Path, class_name: str, method_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
                    return {
                        call.func.attr
                        for call in ast.walk(member)
                        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    }
    raise AssertionError(f"Missing {class_name}.{method_name}")


def test_extracted_orchestration_does_not_depend_on_api_or_flask():
    violations = []
    paths = [*LIFECYCLE_ROOT.glob("*.py")]
    paths.extend(
        ORCHESTRATOR_ROOT / name
        for name in ("graph_builder.py", "execution_runner.py")
    )

    for path in paths:
        illegal = _top_level_imports(path) & {"api", "routes", "flask"}
        if illegal:
            violations.append(f"{path.relative_to(BACKEND_ROOT)}: {sorted(illegal)}")

    assert not violations, "Invalid orchestration dependencies:\n" + "\n".join(
        violations
    )


def test_generator_facade_does_not_build_or_execute_graph_directly():
    path = BACKEND_ROOT / "services" / "blog_generator" / "generator.py"

    assert _method_calls(path, "BlogGenerator", "_build_workflow") == {"build"}
    assert "invoke" not in _method_calls(path, "BlogGenerator", "generate")
    assert "stream" not in _method_calls(path, "BlogGenerator", "generate_stream")


def test_blog_service_generation_paths_delegate_result_finalization():
    path = BACKEND_ROOT / "services" / "blog_generator" / "blog_service.py"

    for method_name in ("_run_generation", "_run_resume"):
        calls = _method_calls(path, "BlogService", method_name)
        assert "finalize" in calls
        assert "save_history" not in calls
