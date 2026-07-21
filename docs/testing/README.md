# VibeBlog Testing Guide

This guide describes the maintained test commands and CI behavior for the Flask backend, Vue frontend, and browser E2E suite.

## Prerequisites

- Python 3.10, 3.11, or 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 20
- npm

Install the backend runtime and test dependencies from the locked environment:

```bash
uv sync --extra test --frozen
```

Install frontend dependencies:

```bash
cd frontend
npm ci
```

## Backend Tests

Run the non-LLM suite used by CI:

```bash
cd backend
uv run --project .. pytest -m "not llm"
```

Run a focused file or test:

```bash
cd backend
uv run --project .. pytest tests/unit/test_database_service.py -v
uv run --project .. pytest tests/unit/test_database_service.py::TestDocumentOperations::test_create_document -v
```

Useful markers declared in `backend/pytest.ini`:

| Marker | Purpose |
| --- | --- |
| `unit` | Fast tests without external dependencies |
| `integration` | Tests that may use the database or filesystem |
| `api` | Flask API endpoint tests |
| `llm` | Tests that call external model APIs |
| `slow` | Long-running tests |

The default pytest configuration writes coverage reports under `backend/`. These files are generated artifacts and must not be committed.

## Frontend Tests

Run the Vitest suite once:

```bash
cd frontend
npm test -- --run
```

Other supported commands:

```bash
npm run test:ui
npm run test:coverage -- --run
```

Frontend tests use Vitest, Vue Test Utils, Testing Library, MSW, and happy-dom. Coverage reports are generated under `frontend/coverage/` and must not be committed.

## Browser E2E Tests

E2E tests require the Flask backend on port 5001 and the Vite frontend on port 5173.

Install the Chromium browser once after syncing Python dependencies:

```bash
uv run playwright install chromium
```

Linux CI or container environments may use `uv run playwright install --with-deps chromium` to install required system libraries as well.

Start both services in one terminal:

```bash
bash docker/start-local.sh
```

Run the complete headless suite in another terminal:

```bash
RUN_E2E_TESTS=1 uv run pytest tests/e2e/ -v
```

Optional controls:

```bash
RUN_E2E_TESTS=1 E2E_HEADED=1 uv run pytest tests/e2e/ -v
RUN_E2E_TESTS=1 E2E_SLOW_MO=100 uv run pytest tests/e2e/ -v
RUN_E2E_TESTS=1 uv run pytest tests/e2e/test_tc01_home_load.py -v
```

E2E screenshots are written to `backend/outputs/e2e_screenshots/` and must not be committed.

## CI And Coverage

| Workflow | Runtime | Command | Enforced coverage gate |
| --- | --- | --- | --- |
| Frontend Tests | Node.js 20 | `npm test` and `npm run test:coverage` | 50% in `frontend/vitest.config.ts` |
| Backend Tests | Python 3.10, 3.11, 3.12 | `uv sync --frozen`, then non-LLM pytest | 20% in the workflow |

Both workflows upload coverage reports to Codecov with separate `frontend` and `backend` flags. Repository-level Codecov behavior is configured in `.github/codecov.yml`.

Coverage percentages change as the codebase evolves. Use the current CI result or a fresh local report instead of documenting a static percentage.

## Before Opening A PR

Run checks proportional to the change:

1. Backend-only change: run the relevant backend tests and the non-LLM suite when shared behavior changes.
2. Frontend-only change: run Vitest and a production build.
3. User workflow change: run the relevant browser E2E cases with both services running.
4. Dependency or CI change: use frozen installation and run the full affected matrix in GitHub Actions.

Do not commit coverage reports, logs, screenshots, caches, uploads, or generated output files.
