# WhatsApp Gateway Removal Design

## Goal

Remove the unused WhatsApp channel integration while preserving the generic
conversational writing API and all core blog-generation behavior.

## Scope

- Delete `integrations/whatsapp-gateway/`, including its Baileys authentication
  helper, runtime gateway, package manifest, and lockfile.
- Remove optional WhatsApp startup, shutdown, authentication migration, log
  cleanup, and user-facing hints from `docker/start-local.sh`.
- Remove WhatsApp-specific ignored runtime paths from `.gitignore`.
- Replace the WhatsApp-specific `X-User-Id` comment in Chat routes with a
  channel-neutral explanation. Do not change request behavior.
- Add a repository retirement contract that prevents the gateway and startup
  hooks from returning while requiring the Chat Blueprint and services to
  remain available.

## Preserved Boundaries

- Every `/api/chat/*` endpoint and its Blueprint registration.
- `backend/services/chat/` and its dispatcher, generation, and session logic.
- `X-User-Id` request isolation behavior for future channel adapters.
- Blog generation, SSE, history, publishing, Dashboard, and frontend behavior.

## Pull Request Coordination

This work is a separate PR based on `origin/main`. PR #157 removes Feishu and
currently contains a test that preserves WhatsApp. Before this PR is merged,
PR #157 must be updated to preserve Chat only, so either PR merge order remains
compatible. Neither PR is merged by Codex.

## Verification

- Use TDD to establish gateway/startup removal and Chat-preservation contracts.
- Run focused Chat and architecture tests, then the complete backend suite.
- Run full frontend Vitest and the production build even though frontend source
  is unchanged.
- Run `uv lock --check`, repository-wide WhatsApp scans, and `git diff --check`.
- Request an independent code review, push, create a ready PR, wait for GitHub
  CI, and backfill Issue #136 without merging.
