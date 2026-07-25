from pathlib import Path

import pytest

from infrastructure.paths import RuntimePaths
from infrastructure.runtime_storage import RuntimeStorage


def _storage(tmp_path: Path) -> RuntimeStorage:
    paths = RuntimePaths.from_env({}, project_root=tmp_path)
    return RuntimeStorage(paths)


def test_write_paths_use_runtime_root(tmp_path):
    storage = _storage(tmp_path)

    assert storage.write_path("logs", "app.log") == tmp_path / "var" / "logs" / "app.log"
    assert storage.write_path("outputs", "images", "cover.png") == (
        tmp_path / "var" / "outputs" / "images" / "cover.png"
    )
    assert storage.write_path("uploads", "paper.pdf") == tmp_path / "var" / "uploads" / "paper.pdf"
    assert storage.write_path("cache", "research") == tmp_path / "var" / "cache" / "research"
    assert storage.write_path("screenshots", "home.png") == (
        tmp_path / "var" / "screenshots" / "home.png"
    )


def test_read_path_prefers_runtime_file(tmp_path):
    storage = _storage(tmp_path)
    current = storage.write_path("outputs", "images", "cover.png")
    legacy = tmp_path / "backend" / "outputs" / "images" / "cover.png"
    current.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    current.write_text("current", encoding="utf-8")
    legacy.write_text("legacy", encoding="utf-8")

    assert storage.read_path("outputs", "images", "cover.png") == current


def test_read_path_falls_back_to_legacy_file(tmp_path):
    storage = _storage(tmp_path)
    legacy = tmp_path / "backend" / "outputs" / "images" / "cover.png"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("legacy", encoding="utf-8")

    assert storage.read_path("outputs", "images", "cover.png") == legacy


def test_read_directories_include_current_then_existing_legacy(tmp_path):
    storage = _storage(tmp_path)
    legacy = tmp_path / "logs"
    legacy.mkdir()

    assert storage.read_directories("logs") == (tmp_path / "var" / "logs", legacy)


def test_storage_does_not_create_directories_during_resolution(tmp_path):
    storage = _storage(tmp_path)

    storage.write_path("outputs", "images")
    storage.read_directories("logs")

    assert not (tmp_path / "var").exists()


@pytest.mark.parametrize("part", ["../secret", "/tmp/secret"])
def test_storage_rejects_paths_outside_runtime_area(tmp_path, part):
    storage = _storage(tmp_path)

    with pytest.raises(ValueError, match="relative path"):
        storage.write_path("outputs", part)
