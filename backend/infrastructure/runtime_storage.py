from pathlib import Path
from typing import Final

from .paths import RuntimePaths


class RuntimeStorage:
    """Resolve new runtime write paths and compatible legacy read paths."""

    _LEGACY_DIRECTORIES: Final[dict[str, tuple[Path, ...]]] = {
        "logs": (Path("logs"),),
        "outputs": (Path("backend/outputs"),),
        "uploads": (Path("backend/uploads"),),
        "cache": (Path("backend/cache"),),
        "screenshots": (Path("backend/outputs/e2e_screenshots"),),
    }

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_path(self, area: str, *parts: str) -> Path:
        self._validate_parts(parts)
        return self._runtime_directory(area).joinpath(*parts)

    def read_path(self, area: str, *parts: str) -> Path:
        self._validate_parts(parts)
        candidates = tuple(directory.joinpath(*parts) for directory in self.read_directories(area))
        return next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    def read_directories(self, area: str) -> tuple[Path, ...]:
        current = self._runtime_directory(area)
        legacy = tuple(
            self.paths.project_root / directory
            for directory in self._LEGACY_DIRECTORIES[area]
            if (self.paths.project_root / directory).exists()
        )
        return (current, *legacy)

    def _runtime_directory(self, area: str) -> Path:
        if area not in self._LEGACY_DIRECTORIES:
            raise ValueError(f"Unknown runtime storage area: {area}")
        return getattr(self.paths, area)

    @staticmethod
    def _validate_parts(parts: tuple[str, ...]) -> None:
        for part in parts:
            path = Path(part)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Runtime storage parts must be a relative path")
