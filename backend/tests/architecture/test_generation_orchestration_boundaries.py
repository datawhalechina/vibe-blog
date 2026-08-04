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


def _method_named_calls(path: Path, class_name: str, method_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
                    return {
                        call.func.id
                        for call in ast.walk(member)
                        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    }
    raise AssertionError(f"Missing {class_name}.{method_name}")


def _function_named_calls(path: Path, function_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    return {
        call.func.id
        for call in ast.walk(function)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }


def test_extracted_orchestration_does_not_depend_on_api_or_flask():
    violations = []
    paths = [*LIFECYCLE_ROOT.glob("*.py")]
    paths.extend(
        ORCHESTRATOR_ROOT / name
        for name in ("graph_builder.py", "execution_runner.py", "routing.py")
    )
    paths.extend((ORCHESTRATOR_ROOT / "nodes").glob("*.py"))

    for path in paths:
        illegal = _top_level_imports(path) & {"api", "routes", "flask"}
        if illegal:
            violations.append(f"{path.relative_to(BACKEND_ROOT)}: {sorted(illegal)}")

    assert not violations, "Invalid orchestration dependencies:\n" + "\n".join(
        violations
    )


def test_generator_facade_does_not_build_or_execute_graph_directly():
    path = BACKEND_ROOT / "services" / "blog_generator" / "generator.py"

    assert _method_calls(path, "BlogGenerator", "_build_workflow") == {
        "_bind_node_handlers",
        "_bind_routing_handlers",
        "build",
    }
    assert "invoke" not in _method_calls(path, "BlogGenerator", "generate")
    assert "stream" not in _method_calls(path, "BlogGenerator", "generate_stream")


def test_generator_has_no_node_or_routing_methods_and_graph_builder_has_no_generator_dependency():
    generator_path = BACKEND_ROOT / "services/blog_generator/generator.py"
    generator_tree = ast.parse(generator_path.read_text(encoding="utf-8"))
    generator_class = next(
        node for node in generator_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "BlogGenerator"
    )
    assert not [
        node.name for node in generator_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.endswith("_node")
    ]
    assert not [
        node.name for node in generator_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("_should_")
    ]

    builder_path = ORCHESTRATOR_ROOT / "graph_builder.py"
    builder_tree = ast.parse(builder_path.read_text(encoding="utf-8"))
    init = next(
        node for node in ast.walk(builder_tree)
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert "generator" not in [argument.arg for argument in init.args.args]

    violations = []
    for path in (ORCHESTRATOR_ROOT / "nodes").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                parameters = {
                    argument.arg for argument in [*node.args.args, *node.args.kwonlyargs]
                }
                if parameters & {"generator", "context"}:
                    violations.append(f"{path.name}:{node.name}")
    routing_path = ORCHESTRATOR_ROOT / "routing.py"
    routing_tree = ast.parse(routing_path.read_text(encoding="utf-8"))
    for node in routing_tree.body:
        if isinstance(node, ast.FunctionDef):
            parameters = {
                argument.arg for argument in [*node.args.args, *node.args.kwonlyargs]
            }
            if parameters & {"generator", "context"}:
                violations.append(f"{routing_path.name}:{node.name}")
    assert not violations


def test_blog_service_generation_paths_delegate_result_finalization():
    path = BACKEND_ROOT / "services" / "blog_generator" / "blog_service.py"

    for method_name in ("_run_generation", "_run_resume"):
        calls = _method_calls(path, "BlogService", method_name)
        assert "finalize" in calls
        assert "save_history" not in calls


def test_blog_service_generation_paths_delegate_stream_and_progress_projection():
    path = BACKEND_ROOT / "services" / "blog_generator" / "blog_service.py"
    stream_path = LIFECYCLE_ROOT / "generation_stream.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    service = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "BlogService"
    )

    forbidden_payload_markers = {
        "researcher_complete",
        "section_complete",
        "writing_chunk",
        "reviewer_complete",
        "assembler_complete",
    }
    for method_name in ("_run_generation", "_run_resume"):
        named_calls = _method_named_calls(path, "BlogService", method_name)
        assert "run_generation_stream" in named_calls
        assert "project_generation_event" not in named_calls
        assert "stream" not in _method_calls(path, "BlogService", method_name)
        method = next(
            node for node in service.body
            if isinstance(node, ast.FunctionDef) and node.name == method_name
        )
        literals = {
            node.value
            for node in ast.walk(method)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        assert not forbidden_payload_markers & literals

    assert "project_event_fn" in _function_named_calls(
        stream_path, "run_generation_stream"
    )
