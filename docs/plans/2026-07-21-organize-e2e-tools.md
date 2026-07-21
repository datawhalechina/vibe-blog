# Organize E2E Tools Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move E2E-only helper scripts out of the repository root tooling directory and colocate them with the E2E suite.

**Architecture:** Place executable helpers in `tests/e2e/tools/` while keeping test cases directly under `tests/e2e/`. Recalculate the repository root from the deeper location, update cross-script and documentation references, and preserve all existing command-line options and output paths.

**Tech Stack:** Bash, Python, pytest, Playwright

---

### Task 1: Relocate E2E tools

**Files:**
- Move: `scripts/run_e2e.sh` to `tests/e2e/tools/run_e2e.sh`
- Move: `scripts/analyze_e2e_logs.py` to `tests/e2e/tools/analyze_logs.py`
- Modify: `tests/e2e/tools/run_e2e.sh`

1. Move both files without changing their behavior.
2. Update repository-root discovery for the deeper directory.
3. Update the runner's analyzer path.
4. Run shell syntax and Python compilation checks.

### Task 2: Update maintained documentation

**Files:**
- Modify: `docs/testing/README.md`
- Modify: `CHANGELOG.md`

1. Document the one-command E2E runner and log analyzer paths.
2. Record the repository organization change.
3. Search for stale `scripts/` references.

### Task 3: Verify and publish

1. Exercise non-destructive runner argument and service-guard paths.
2. Run the analyzer against an empty temporary runtime layout.
3. Review the complete diff, push the branch, and create a focused PR.
