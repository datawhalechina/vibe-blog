from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RuntimePaths:
    project_root: Path
    runtime_root: Path
    logs: Path
    outputs: Path
    uploads: Path
    cache: Path
    screenshots: Path

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        project_root: Path | None = None,
    ) -> "RuntimePaths":
        env = os.environ if environ is None else environ
        root = (project_root or _PROJECT_ROOT).resolve()
        runtime_value = env.get("VIBE_RUNTIME_DIR", "var")
        if not runtime_value.strip():
            runtime_value = "var"
        runtime_root = Path(runtime_value).expanduser()
        if not runtime_root.is_absolute():
            runtime_root = root / runtime_root
        runtime_root = runtime_root.resolve()

        return cls(
            project_root=root,
            runtime_root=runtime_root,
            logs=runtime_root / "logs",
            outputs=runtime_root / "outputs",
            uploads=runtime_root / "uploads",
            cache=runtime_root / "cache",
            screenshots=runtime_root / "screenshots",
        )
