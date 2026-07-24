# Runtime Path Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce one side-effect-free source of truth for the target `var/` runtime layout without changing any existing runtime consumer.

**Architecture:** Add an immutable `RuntimePaths` value object under `backend/infrastructure/`. It resolves the repository root, an optional `VIBE_RUNTIME_DIR`, and the five target runtime categories, but it never creates or moves data. Existing configuration and call sites remain untouched until the next PR.

**Tech Stack:** Python 3.10+, pathlib, dataclasses, pytest, uv

---

### Task 1: Specify runtime path resolution

**Files:**
- Create: `backend/tests/unit/test_runtime_paths.py`

**Step 1: Write failing default-layout tests**

```python
from pathlib import Path

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
```

**Step 2: Write failing environment-override tests**

```python
def test_resolves_relative_runtime_override_from_project_root(tmp_path: Path) -> None:
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
```

**Step 3: Run tests and verify RED**

Run:

```bash
cd backend
UV_CACHE_DIR=/private/tmp/vibe-blog-uv-cache-runtime-paths uv run --frozen pytest tests/unit/test_runtime_paths.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'infrastructure.paths'`.

### Task 2: Implement the side-effect-free path object

**Files:**
- Create: `backend/infrastructure/paths.py`
- Modify: `backend/infrastructure/__init__.py`
- Test: `backend/tests/unit/test_runtime_paths.py`

**Step 1: Add the minimal implementation**

```python
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
        runtime_root = Path(env.get("VIBE_RUNTIME_DIR", "var")).expanduser()
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
```

**Step 2: Export the public boundary**

```python
from .paths import RuntimePaths

__all__ = ["RuntimePaths"]
```

**Step 3: Run focused tests and verify GREEN**

Run:

```bash
cd backend
UV_CACHE_DIR=/private/tmp/vibe-blog-uv-cache-runtime-paths uv run --frozen pytest tests/unit/test_runtime_paths.py -v
```

Expected: 3 tests pass.

### Task 3: Document the boundary

**Files:**
- Create: `docs/architecture/runtime-paths.md`
- Modify: `.gitignore`
- Modify: `CHANGELOG.md`

**Step 1: Document the target layout and compatibility contract**

Document `VIBE_RUNTIME_DIR`, all five derived paths, and these constraints:

- no directories are created during import or resolution;
- existing consumers continue using their current locations in this PR;
- old data is never moved or deleted automatically;
- consumer migration occurs in later focused PRs.

**Step 2: Make the root ignore rule explicit**

Replace the generic `var/` rule with `/var/` so only repository runtime state is hidden.

**Step 3: Update the changelog**

Add the plan and runtime-path foundation entries under `2026-07-25`.

**Step 4: Verify ignore behavior**

Run:

```bash
git check-ignore -v var/logs/example.log
git check-ignore -q backend/var/example
```

Expected: the root path is ignored; the nested path is not ignored by the root-specific rule.

### Task 4: Run regression and end-to-end gates

**Files:**
- No committed file changes.

**Step 1: Run the complete non-LLM backend suite**

```bash
cd backend
UV_CACHE_DIR=/private/tmp/vibe-blog-uv-cache-runtime-paths uv run --frozen pytest -v -m "not llm"
```

Expected: all selected tests pass.

**Step 2: Run frontend tests and production build**

```bash
cd frontend
npm ci
npm test -- --run
npm run build
```

Expected: tests and build pass.

**Step 3: Start the actual local stack**

```bash
bash docker/start-local.sh
```

Expected: Flask listens on 5001, Vite listens on 5173, and `GET /health` succeeds.

**Step 4: Run browser smoke E2E**

```bash
RUN_E2E_TESTS=1 backend/.venv/bin/python -m pytest \
  tests/e2e/test_tc01_home_load.py \
  tests/e2e/test_tc07_navigation.py \
  tests/e2e/test_tc08_theme.py -v
```

Expected: all smoke cases pass without using an LLM API.

**Step 5: Verify the final diff**

```bash
git diff --check
git status --short
rg -n "RuntimePaths|VIBE_RUNTIME_DIR" backend docs
```

Expected: no whitespace errors, no generated artifacts, and no existing runtime consumer imports the new module.

### Task 5: Review and publish

**Files:**
- No additional implementation files.

**Step 1: Request independent code review**

Review the complete diff against the repository organization design and the no-behavior-change constraint.

**Step 2: Push and create one focused PR**

Use title:

```text
refactor: establish centralized runtime path configuration
```

The PR description must include unit, backend, frontend, startup, health, and Playwright E2E evidence.
