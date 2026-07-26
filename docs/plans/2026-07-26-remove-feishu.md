# Feishu Integration Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Completely remove the Feishu interaction integration without changing Chat or WhatsApp behavior.

**Architecture:** Remove the Feishu API adapter at the HTTP/deployment boundary and add a static repository contract that prevents it from returning. Keep the underlying chat-writing domain independent and unchanged.

**Tech Stack:** Flask, pytest, Docker Compose, Vue/Vitest verification.

---

### Task 1: Add The Retirement Contract

**Files:**
- Create: `backend/tests/architecture/test_no_feishu_integration.py`

**Step 1: Write the failing test**

Add assertions that production Feishu modules do not exist, the route registry
does not mention `feishu_bp`, Docker Compose has no `FEISHU_` configuration,
the old URL is absent from registered Flask routes, and Chat/WhatsApp remain.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/architecture/test_no_feishu_integration.py -v`

Expected: FAIL because the Feishu modules, blueprint registration, and Docker
variables still exist.

**Step 3: Commit the RED contract**

```bash
git add backend/tests/architecture/test_no_feishu_integration.py
git commit -m "test: define Feishu retirement contract"
```

### Task 2: Remove The Backend Adapter

**Files:**
- Delete: `backend/api/routes/feishu_routes.py`
- Delete: `backend/routes/feishu_routes.py`
- Modify: `backend/api/routes/__init__.py`
- Modify: `backend/tests/unit/test_api_import_compat.py`

**Step 1: Remove Feishu imports and blueprint registration**

Delete the implementation and legacy alias, then remove `feishu_routes` from
the compatibility module list and `feishu_bp` from `register_all_blueprints`.

**Step 2: Run focused tests**

Run:

```bash
python -m pytest \
  tests/architecture/test_no_feishu_integration.py \
  tests/unit/test_api_import_compat.py -v
```

Expected: the backend-removal assertions pass; deployment assertion remains
RED until Task 3.

### Task 3: Remove Deployment Configuration And Record The Change

**Files:**
- Modify: `docker/docker-compose.yml`
- Modify: `CHANGELOG.md`

**Step 1: Remove Feishu environment variables**

Delete the Feishu-only comment and `FEISHU_APP_ID`, `FEISHU_APP_SECRET`,
`FEISHU_VERIFICATION_TOKEN`, and `FEISHU_ENCRYPT_KEY` entries.

**Step 2: Update the changelog**

Under `## 2026-07-26` / `### Changed`, add a refactor entry describing the
hard removal and explicit preservation of Chat and WhatsApp.

**Step 3: Run the retirement contract GREEN**

Run: `python -m pytest tests/architecture/test_no_feishu_integration.py -v`

Expected: PASS.

**Step 4: Commit the implementation**

```bash
git add CHANGELOG.md docker/docker-compose.yml backend/api/routes \
  backend/routes backend/tests
git commit -m "refactor: remove Feishu integration"
```

### Task 4: Verify The Preserved Boundaries

**Files:** No production edits expected.

**Step 1: Run focused backend tests**

```bash
python -m pytest \
  tests/architecture/test_no_feishu_integration.py \
  tests/unit/test_api_import_compat.py \
  tests/test_chat_routes.py \
  tests/test_chat_generate.py \
  tests/test_agent_dispatcher.py \
  tests/test_writing_session.py -v
```

**Step 2: Run complete backend tests**

Run: `python -m pytest tests/ -v`

**Step 3: Run frontend verification**

Run: `npm test -- --run`, then `npm run build` from `frontend/`.

**Step 4: Run repository checks**

Run:

```bash
uv lock --check
git diff --check
rg -n -i "feishu|飞书" . --glob '!CHANGELOG.md' --glob '!docs/plans/**'
```

Expected: lock and diff checks pass; production scan returns no matches.

### Task 5: Review And Create The PR

**Step 1: Request independent code review**

Review the diff against the approved design, especially preservation of Chat
and WhatsApp.

**Step 2: Fix all blocking findings and rerun affected gates**

**Step 3: Push and create a PR**

Push `codex/remove-feishu-integration` and create a non-draft PR linked to
Issue #136. Wait for GitHub CI and report its result. Do not merge the PR.
