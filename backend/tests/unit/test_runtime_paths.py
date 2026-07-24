from pathlib import Path

import pytest

from infrastructure.paths import RuntimePaths


def test_defaults_to_repository_var_layout(tmp_path: Path) -> None:
    paths = RuntimePaths.from_env({}, project_root=tmp_path)

    assert paths.project_root == tmp_path
    assert paths.runtime_root == tmp_path / "var"
    assert paths.logs == tmp_path / "var" / "logs"
    assert paths.outputs == tmp_path / "var" / "outputs"
    assert paths.uploads == tmp_path / "var" / "uploads"
    assert paths.cache == tmp_path / "var" / "cache"
    assert paths.screenshots == tmp_path / "var" / "screenshots"
    assert not paths.runtime_root.exists()


def test_resolves_relative_runtime_override_from_project_root(
    tmp_path: Path,
) -> None:
    paths = RuntimePaths.from_env(
        {"VIBE_RUNTIME_DIR": "state"},
        project_root=tmp_path,
    )

    assert paths.runtime_root == tmp_path / "state"


def test_preserves_absolute_runtime_override(tmp_path: Path) -> None:
    target = tmp_path / "external-state"

    paths = RuntimePaths.from_env(
        {"VIBE_RUNTIME_DIR": str(target)},
        project_root=tmp_path / "project",
    )

    assert paths.runtime_root == target


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_runtime_override_uses_default(
    tmp_path: Path,
    value: str,
) -> None:
    paths = RuntimePaths.from_env(
        {"VIBE_RUNTIME_DIR": value},
        project_root=tmp_path,
    )

    assert paths.runtime_root == tmp_path / "var"
