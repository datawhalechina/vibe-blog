# Remove Vercel Support And Relocate uv Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove Vercel-specific deployment behavior and make `backend/` the self-contained Python project root.

**Architecture:** Delete the unused root serverless entry and its read-only fallbacks, while preserving the normal Flask and Docker entry paths. Move the uv manifest and lock file together, then update every maintained CI and documentation consumer to resolve the project from `backend/`.

**Tech Stack:** Flask, uv, pytest, GitHub Actions, YAML

---

### Task 1: Remove Vercel deployment support

**Files:**
- Delete: `vercel.json`
- Delete: `api/index.py`
- Modify: `backend/api/__init__.py`
- Modify: `backend/logging_config.py`
- Modify: `backend/services/database_service.py`
- Modify: `CHANGELOG.md`

1. Delete the Vercel configuration and serverless entry point.
2. Remove temporary-upload, in-memory-database, and console-only logging fallbacks for read-only runtimes.
3. Add a `Changed` changelog entry describing removal of Vercel support.
4. Search for stale Vercel deployment references and run focused startup/database/logging tests.
5. Commit the focused removal.

### Task 2: Move the uv project into backend

**Files:**
- Move: `pyproject.toml` to `backend/pyproject.toml`
- Move: `uv.lock` to `backend/uv.lock`
- Modify: `.github/workflows/test-backend.yml`
- Modify: `docs/testing/README.md`
- Modify: `CHANGELOG.md`

1. Move the manifest and lock file together and update the README metadata path.
2. Change backend CI to install and execute from `backend/`.
3. Update maintained testing commands for the new project location.
4. Add a `Changed` changelog entry describing the new Python project root.
5. Run `uv lock --check --project backend`, a frozen sync, workflow parsing, stale-reference searches, and the non-LLM backend test suite.
6. Commit the migration.

### Task 3: Review and publish

**Files:**
- Review all files changed from `origin/main`.

1. Run `git diff --check` and verify the exact deletion/move set.
2. Request an independent code review.
3. Fix any actionable findings and rerun affected checks.
4. Push the branch and create a focused pull request without merging it automatically.
