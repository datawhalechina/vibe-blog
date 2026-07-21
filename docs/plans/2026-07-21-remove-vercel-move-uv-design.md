# Remove Vercel Support And Relocate uv Configuration

## Goal

Remove the repository's Vercel deployment path and make `backend/` the Python project root.

## Scope

- Delete `vercel.json` and the root `api/index.py` serverless entry point.
- Remove the three read-only-runtime fallbacks that were retained for Vercel: temporary uploads, in-memory database fallback, and console-only logging fallback.
- Move `pyproject.toml` and `uv.lock` into `backend/` as one atomic uv project.
- Update backend CI and maintained testing documentation to run uv from `backend/`.
- Preserve Docker, local Flask startup, backend requirements files, frontend behavior, and application APIs.

## Behavior

Local and Docker startup continue to use `backend/app.py` and Gunicorn. Runtime directories must now be writable; directory creation failures are surfaced instead of silently changing storage or logging behavior. Vercel deployment is no longer supported by repository configuration.

The uv environment moves from `.venv/` at the repository root to `backend/.venv/`. Commands run from the repository root use `uv --project backend`; commands run inside `backend/` use plain `uv` commands.

## Verification

- Validate the relocated lock file with `uv lock --check --project backend`.
- Perform a frozen dependency sync from `backend/`.
- Run the backend non-LLM test suite with the same coverage threshold as CI.
- Parse the updated workflow YAML and search for stale root-level uv and Vercel references.
- Confirm frontend and Docker files are unchanged except where explicitly required.
