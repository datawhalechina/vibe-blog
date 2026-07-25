---
name: vibe-blog-e2e-verification
description: Use when validating VibeBlog changes that affect Flask APIs, Vue routes, service startup, SSE progress, generation, history, details, publishing, scheduling, or other user-facing workflows.
---

# VibeBlog E2E Verification

## Overview

Verify changed boundaries and core workflows with tracked commands. Treat exit codes, HTTP, browser errors, artifacts, and Git state as separate gates.

## Select Scope

| Change | Required browser scope |
| --- | --- |
| Frontend-only cleanup | Affected Vitest, full Vitest, build, affected Playwright case |
| Flask Blueprint, API, startup, config, or service initialization | Backend tests, `/health`, smoke E2E |
| Generation, SSE, history, details, publishing, or shared infrastructure | Full non-LLM tests and full E2E suite |

Use the broader scope when a change crosses rows. Never claim E2E coverage when pytest skipped the suite because `RUN_E2E_TESTS` was unset.

## Establish Baseline

Run from the worktree root:

```bash
git status --short --branch
uv lock --project backend --check
uv sync --project backend --extra test --frozen
npm ci --prefix frontend
```

Record existing Git changes. Keep artifacts under ignored `var/`. Do not attach deployment `.env` before static tests; feature toggles and background tasks pollute isolation. Provide it only for browser E2E.

## Run Static Gates

```bash
uv run --project backend pytest backend/tests -m "not llm" -q
npm test --prefix frontend -- --run
npm run build --prefix frontend
git diff --check
```

For narrow frontend deletion, run affected tests first. Treat plan searches as acceptance tests.

## Run Browser Gates

Use the tracked runner; do not rely on local `.claude/` or `.Codex/` files:

```bash
bash tests/e2e/tools/run_e2e.sh --restart --smoke
bash tests/e2e/tools/run_e2e.sh --restart
```

Smoke covers home and real mini generation. Use full mode for shared behavior and Issue #136. Inspect the newest `var/logs/e2e_result_*.log`; require zero failures and errors instead of trusting the banner.

For focused changes, run a named case while services run:

```bash
RUN_E2E_TESTS=1 uv run --project backend pytest tests/e2e/test_tc13_dashboard.py -v
```

Require all applicable checks:

- `GET http://127.0.0.1:5001/health` returns HTTP 200.
- Home editor, generate action, theme, history, and blog detail navigation work.
- Generation receives SSE progress and reaches a detail page; cancellation or outline confirmation works when in scope.
- No new `console.error`, `pageerror`, failed API request, blank page, or unexpected 404/5xx appears.
- Screenshots under `var/screenshots/` show rendered content without overlap.

## Finish Cleanly

Stop only services started for verification. Confirm ports 5001 and 5173 are released, then run:

```bash
git status --short --branch
git diff --check
git ls-files var frontend/dist frontend/coverage backend/outputs
```

The last command must reveal no newly tracked artifacts. Compare final status with the baseline and report exact pass, fail, and skip counts plus external limitations.

## Common Mistakes

- Using `python -m pytest` outside the locked backend environment instead of `uv run --project backend`.
- Writing screenshots to legacy `backend/outputs/e2e_screenshots/`.
- Treating a listening port as readiness without an HTTP check.
- Ignoring browser console or page errors because pytest exited zero.
- Deleting or reverting pre-existing worktree changes during cleanup.
