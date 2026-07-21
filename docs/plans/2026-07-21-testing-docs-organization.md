# Testing Documentation Organization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move testing documentation and Codecov configuration out of the repository root, remove the obsolete implementation report, and keep all retained information accurate and verifiable.

**Architecture:** Long-lived operational documentation lives under `docs/testing/`; GitHub service configuration lives under `.github/`. The testing guide derives commands and thresholds from current project configuration and avoids static coverage claims.

**Tech Stack:** Markdown, GitHub Actions, Codecov YAML, Vitest, pytest, uv

---

### Task 1: Rewrite the testing guide

**Files:**
- Create: `docs/testing/README.md`
- Delete: `TESTING.md`
- Modify: `README.md`

**Step 1:** Write a concise guide covering prerequisites, frontend tests, backend tests, E2E tests, markers, generated reports, CI matrices, and current enforced thresholds.

**Step 2:** Add a discoverable testing-documentation link to `README.md`.

**Step 3:** Remove the stale root testing guide.

**Step 4:** Verify that `YOUR_USERNAME`, obsolete Node 18 matrix claims, and static coverage snapshots are absent.

### Task 2: Remove the historical implementation report

**Files:**
- Delete: `TESTING_IMPLEMENTATION_SUMMARY.md`

**Step 1:** Confirm no maintained documentation links to the report.

**Step 2:** Delete the report; rely on Git history and `CHANGELOG.md` for historical context.

### Task 3: Move and repair Codecov configuration

**Files:**
- Create: `.github/codecov.yml`
- Delete: `codecov.yml`
- Modify: `.github/workflows/test-backend.yml`
- Modify: `.github/workflows/test-frontend.yml`

**Step 1:** Move the repository-level Codecov settings under `.github/`.

**Step 2:** Define valid named project statuses scoped to the `frontend` and `backend` flags, using 50% and 20% targets respectively, and disable unrelated default and patch statuses.

**Step 3:** Add `.github/codecov.yml` to both workflow path filters so configuration-only PRs run coverage validation.

**Step 4:** Run the official validator:

```bash
curl --data-binary @.github/codecov.yml https://api.codecov.io/validate
```

Expected: a successful validation response.

### Task 4: Record and verify the change

**Files:**
- Modify: `CHANGELOG.md`

**Step 1:** Add a 2026-07-21 Changed entry covering testing documentation and Codecov organization.

**Step 2:** Run YAML parsing, stale-reference searches, `git diff --check`, and `uv lock --check`.

**Step 3:** Review the final diff and confirm no application code or generated reports are included.

**Step 4:** Commit all scoped files with a documentation-oriented commit message.
