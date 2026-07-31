import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATABASE_REPOSITORY_ROOT = BACKEND_ROOT / "repositories" / "database"
DATABASE_SERVICE_PATH = BACKEND_ROOT / "services" / "database_service.py"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    return imported


def test_database_repositories_do_not_depend_on_upper_layers():
    forbidden = {"api", "routes", "services", "flask"}
    violations = []

    for path in DATABASE_REPOSITORY_ROOT.glob("*.py"):
        illegal = _imports(path) & forbidden
        if illegal:
            violations.append(f"{path.name}: {sorted(illegal)}")

    assert not violations, "Invalid repository dependencies:\n" + "\n".join(violations)


def test_database_service_facade_contains_no_sql_execution():
    tree = ast.parse(
        DATABASE_SERVICE_PATH.read_text(encoding="utf-8"),
        filename=str(DATABASE_SERVICE_PATH),
    )
    sql_calls = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"execute", "executescript"}
        ):
            sql_calls.append(node.lineno)

    assert not sql_calls, f"DatabaseService must remain a SQL-free facade: {sql_calls}"
