# WhatsApp Gateway Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the unused WhatsApp channel adapter and all of its startup hooks without changing `/api/chat/*` or core blog-generation behavior.

**Architecture:** Treat WhatsApp as an optional edge adapter around the generic Chat API. Delete that adapter and its local-development wiring, then enforce the boundary with a static/runtime architecture contract that keeps Chat registered and functional.

**Tech Stack:** Node.js gateway, Bash local runner, Flask Chat Blueprint, pytest architecture tests, Vue/Vitest verification.

---

### Task 1: Make PR #157 Compatible With WhatsApp Retirement

**Files:**
- Modify: `/private/tmp/vibe-blog-remove-feishu/backend/tests/architecture/test_no_feishu_integration.py`
- Modify: `/private/tmp/vibe-blog-remove-feishu/docs/plans/2026-07-26-remove-feishu-design.md`
- Modify: `/private/tmp/vibe-blog-remove-feishu/docs/plans/2026-07-26-remove-feishu.md`
- Modify: `/private/tmp/vibe-blog-remove-feishu/CHANGELOG.md`

**Step 1: Remove the WhatsApp preservation assertion**

Rename the preserved-boundary test to cover Chat only and remove the filesystem
assertion for `integrations/whatsapp-gateway/src/index.js`.

**Step 2: Update PR documentation**

State that Feishu removal preserves Chat and that WhatsApp retirement is handled
by a separate product decision and PR. Remove claims that PR #157 permanently
requires WhatsApp.

**Step 3: Run focused verification**

Run:

```bash
cd /private/tmp/vibe-blog-remove-feishu/backend
python -m pytest tests/architecture/test_no_feishu_integration.py tests/test_chat_routes.py -q --no-cov
```

Expected: all tests pass and Chat remains registered.

**Step 4: Commit, push, and wait for PR #157 CI**

```bash
git add CHANGELOG.md backend/tests/architecture/test_no_feishu_integration.py docs/plans/
git commit -m "test: decouple Feishu retirement from WhatsApp"
git push
gh pr checks 157 --watch
```

Expected: PR #157 remains open and all triggered checks pass. Do not merge.

### Task 2: Define the WhatsApp Retirement Contract

**Files:**
- Create: `backend/tests/architecture/test_no_whatsapp_gateway.py`
- Modify: `CHANGELOG.md`

**Step 1: Write the failing contract**

Add tests that require:

```python
assert not (PROJECT_ROOT / "integrations/whatsapp-gateway").exists()
assert "ENABLE_WHATSAPP" not in start_script
assert "WHATSAPP_DIR" not in start_script
assert "whatsapp-gateway" not in gitignore.lower()
assert "chat_bp" in route_registry
assert (BACKEND_ROOT / "services/chat").is_dir()
```

Register all Flask Blueprints and assert at least one `/api/chat/` rule remains.

**Step 2: Run the contract to verify RED**

Run:

```bash
cd backend
python -m pytest tests/architecture/test_no_whatsapp_gateway.py -q --no-cov
```

Expected: gateway, startup, and ignore assertions fail while Chat assertions pass.

### Task 3: Remove the WhatsApp Adapter and Startup Wiring

**Files:**
- Delete: `integrations/whatsapp-gateway/src/index.js`
- Delete: `integrations/whatsapp-gateway/src/auth.js`
- Delete: `integrations/whatsapp-gateway/package.json`
- Delete: `integrations/whatsapp-gateway/package-lock.json`
- Modify: `docker/start-local.sh`
- Modify: `.gitignore`
- Modify: `backend/api/routes/chat_routes.py`
- Modify: `CHANGELOG.md`

**Step 1: Delete the standalone gateway**

Remove the complete tracked directory. Do not change any file under
`backend/services/chat/` or remove `chat_bp`.

**Step 2: Remove local-runner integration**

Delete WhatsApp variables, legacy credential migration, dependency install,
optional process startup, cleanup, log rotation, status, and usage hints.

**Step 3: Keep the user isolation behavior channel-neutral**

Retain `X-User-Id` handling exactly as implemented. Replace only the docstring
that names WhatsApp/NanoClaw with a generic channel-adapter explanation.

**Step 4: Run focused GREEN verification**

Run:

```bash
cd backend
python -m pytest \
  tests/architecture/test_no_whatsapp_gateway.py \
  tests/test_chat_routes.py \
  tests/test_chat_generate.py \
  tests/test_agent_dispatcher.py \
  tests/test_writing_session.py -q
```

Expected: all tests pass.

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove WhatsApp gateway"
```

### Task 4: Verify and Submit the Independent PR

**Files:**
- Verify all changed files and repository state.

**Step 1: Run backend and lock gates**

```bash
uv lock --project backend --check
uv run --project backend pytest backend/tests -m "not llm" -q
```

Expected: lock is current and the complete backend suite passes apart from
documented skips.

**Step 2: Run frontend gates**

```bash
npm ci --prefix frontend
npm test --prefix frontend -- --run
npm run build --prefix frontend
```

Expected: all Vitest tests and production build pass.

**Step 3: Run acceptance scans**

```bash
rg -n -i --hidden "whatsapp|ENABLE_WHATSAPP|WHATSAPP_DIR" . \
  --glob '!.git' --glob '!CHANGELOG.md' --glob '!docs/plans/**' \
  --glob '!backend/tests/**' --glob '!frontend/node_modules/**'
git diff --check
git status --short --branch
```

Expected: no production/startup references, clean diff, and no generated files.

**Step 4: Request independent code review**

Review `origin/main..HEAD` for accidental Chat deletion, startup regressions,
missed credential paths, and inadequate retirement tests. Fix all Critical and
Important findings and rerun affected gates.

**Step 5: Push and create PR**

```bash
git push -u origin codex/remove-whatsapp-gateway
gh pr create --base main --head codex/remove-whatsapp-gateway
gh pr checks <number> --watch
```

Expected: ready, open PR with successful CI. Do not merge.

**Step 6: Backfill Issue #136**

Comment with the product decision, PR URL, exact verification counts, CI state,
and an explicit statement that the PR remains open for manual squash merge.
