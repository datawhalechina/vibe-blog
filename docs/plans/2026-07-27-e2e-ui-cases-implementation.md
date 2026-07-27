# E2E UI Cases Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair seven stale/flaky UI E2E cases and make the tracked runner report pytest failures correctly.

**Architecture:** Keep selectors centralized in `backend/tests/e2e_utils.py`, expose the quality action through an accessible button contract, and keep animated decoration separate from click targets. Protect the contracts with a repository-level architecture test.

**Tech Stack:** Python/pytest, Playwright, Vue 3 SFC, Bash, Vitest/Vite

---

### Task 1: Add RED repository contracts

**Files:**
- Create: `backend/tests/architecture/test_e2e_ui_contracts.py`

**Steps:**
1. Assert the runner contains `set -o pipefail`.
2. Assert TC11 and TC12 do not use `textarea.code-input-textarea`.
3. Assert TC14 does not select the last SVG toolbar button.
4. Assert the scroll animation is not applied to `.scroll-hint`.
5. Run `uv run --project backend pytest backend/tests/architecture/test_e2e_ui_contracts.py -q` and verify the expected failures.

### Task 2: Preserve runner exit status

**Files:**
- Modify: `tests/e2e/tools/run_e2e.sh`

**Steps:**
1. Replace `set -e` with strict error handling that includes `pipefail`.
2. Run the architecture contract and verify the runner assertion passes.

### Task 3: Update TipTap-aware E2E input usage

**Files:**
- Modify: `tests/e2e/test_tc11_responsive.py`
- Modify: `tests/e2e/test_tc12_error.py`

**Steps:**
1. Import and use `find_element`, `fill_input`, and `INPUT_SELECTORS`.
2. Assert the discovered contenteditable editor and generate button are visible/disabled as appropriate.
3. Run the architecture contract and focused tests.

### Task 4: Stabilize quality action and history click target

**Files:**
- Modify: `frontend/src/views/Generate.vue`
- Modify: `frontend/src/views/Home.vue`
- Modify: `tests/e2e/test_tc14_quality_eval.py`

**Steps:**
1. Add an accessible label/test contract to the quality action.
2. Select the action by role/name in TC14.
3. Move the bounce animation from `.scroll-hint` to `.scroll-hint-arrow`.
4. Run the architecture contract and focused Playwright cases.

### Task 5: Verify and commit

**Files:**
- Modify: `CHANGELOG.md`

**Steps:**
1. Record the runner and UI E2E fixes under `2026-07-27`.
2. Run backend non-LLM tests, frontend tests, build, focused E2E, `git diff --check`, and artifact hygiene checks.
3. Review the diff, commit, push, and create a PR with `Refs #160`.
