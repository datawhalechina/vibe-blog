# Feishu Integration Removal Design

## Status

Approved for immediate removal on 2026-07-26.

## Goal

Remove the Feishu interaction surface completely while preserving the shared
chat-writing services.

## Scope

- Delete the Feishu webhook blueprint and all Feishu API/card/progress helpers.
- Delete the legacy `routes.feishu_routes` compatibility alias.
- Stop registering `/api/feishu/webhook`; the retired URL will return 404.
- Remove Feishu-only Docker environment variables.
- Remove Feishu from route import compatibility expectations.
- Add a repository contract that rejects Feishu production modules,
  registrations, routes, and deployment configuration.
- Record the removal in `CHANGELOG.md`.

## Preserved Boundaries

- Keep `/api/chat/*`, `services/chat/*`, and their tests.
- Treat other channel adapters as separate product decisions and PRs.
- Do not change blog generation, task streaming, or scheduler behavior.

## Error And Compatibility Behavior

This is a hard removal, not a feature flag or tombstone. Calls to the old
Feishu webhook receive Flask's normal 404 response. No compatibility import is
kept because retaining it would preserve an unsupported production boundary.

## Verification

- Run a focused retirement contract test first in RED, then GREEN.
- Run API import compatibility and Chat tests.
- Run the complete backend non-LLM test suite.
- Run the complete frontend test suite and production build because the PR
  changes shared repository/deployment metadata.
- Run `uv lock --check`, `git diff --check`, and repository-wide Feishu scans.
- Push and create a PR only; never merge it automatically.
