import ast
import importlib
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2]

BOUNDARY_PACKAGES = (
    "repositories",
    "repositories.database",
    "repositories.documents",
    "repositories.tasks",
    "models",
    "shared",
    "infrastructure.config",
    "infrastructure.database",
    "infrastructure.logging",
)

FORBIDDEN_IMPORTS = {
    "services": {"api", "routes", "flask"},
    "repositories": {"api", "routes", "services", "flask"},
    "models": {"api", "routes", "services", "repositories", "infrastructure", "flask"},
    "shared": {"api", "routes", "services", "repositories", "infrastructure", "flask"},
    "infrastructure": {"api", "routes", "services", "repositories", "flask"},
}

LEGACY_ALLOWED_IMPORTS = {
    Path("services/blog_generator/queue_bridge.py"): {"flask"},
    Path("services/blog_generator/blog_service.py"): {"flask"},
}


@pytest.mark.parametrize("package", BOUNDARY_PACKAGES)
def test_boundary_package_is_importable(package):
    assert importlib.import_module(package)


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def _find_forbidden_imports(path: Path, forbidden: set[str]) -> set[str]:
    return {
        imported
        for imported in _top_level_imports(path)
        if any(
            imported == prefix or imported.startswith(f"{prefix}_")
            for prefix in forbidden
        )
    }


def test_flask_extensions_are_treated_as_framework_imports(tmp_path):
    source = tmp_path / "example.py"
    source.write_text("from flask_cors import CORS\n", encoding="utf-8")

    assert _find_forbidden_imports(source, {"flask"}) == {"flask_cors"}


def test_relative_imports_cannot_escape_a_boundary(tmp_path):
    source = tmp_path / "example.py"
    source.write_text("from ..services import generator\n", encoding="utf-8")

    assert _find_forbidden_imports(source, {"services"}) == {"services"}


@pytest.mark.parametrize("package,forbidden", FORBIDDEN_IMPORTS.items())
def test_lower_layers_do_not_import_upper_layers(package, forbidden):
    violations = []
    for path in (BACKEND_ROOT / package).rglob("*.py"):
        relative_path = path.relative_to(BACKEND_ROOT)
        illegal = _find_forbidden_imports(path, forbidden) - LEGACY_ALLOWED_IMPORTS.get(
            relative_path, set()
        )
        if illegal:
            violations.append(f"{relative_path}: {sorted(illegal)}")

    assert not violations, "Invalid dependency direction:\n" + "\n".join(violations)
