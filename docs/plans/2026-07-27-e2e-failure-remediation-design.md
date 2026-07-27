# E2E Failure Remediation Design

## Context

The full E2E run on `origin/main` at `36e430e` collected 42 tests and finished with 32 passed and 10 failed. Seven failures are stale or unstable UI tests. Three failures come from live generation exceeding the test deadline while external deep-scrape providers retry.

Issue #160 tracks the evidence and acceptance criteria.

## Delivery Boundaries

### PR 1: UI E2E contracts and runner correctness

- Make the shell runner preserve pytest's exit status through `tee`.
- Reuse the shared TipTap-aware input selectors in responsive and validation tests.
- Select the quality action by a stable accessible contract instead of toolbar position.
- Keep the history navigation click target stationary by animating its child arrow.
- Add architecture tests that reject the stale selector and runner patterns.

This PR does not change API, SSE, generation, or persistence behavior.

### PR 2: Live generation budget and completion waits

- Bound external deep scraping by per-request and total deadlines, with a smaller mini preset.
- Stop waiting on unavailable sources after enough useful material has succeeded.
- Centralize E2E task completion/history readiness polling.
- Make TC02, TC15, and TC16 fail at the actual incomplete state instead of navigating to a missing history record.

This PR preserves API payloads, event names, graph ordering, and database schemas.

## Testing Strategy

PR 1 uses a repository contract test as the RED gate, then runs affected Playwright cases, full backend non-LLM tests, frontend Vitest, and production build. PR 2 adds unit tests for deadline/retry policy and polling helpers before changing implementation, then runs focused live E2E and the same static gates.

The full live suite remains evidence-based: its pytest summary and exit code are authoritative, not the runner banner.
