# Repository Organization Design

## Goal

Improve repository clarity and backend ownership boundaries without repeating the high-risk, all-at-once directory migration proposed in PR #111.

The migration must remain compatible with existing startup commands, API routes, Docker paths, and commonly used Python imports until each replacement boundary has been verified.

## Current Problems

- Generated runtime data is spread across root-level and backend-level `logs`, `outputs`, uploads, screenshots, caches, and coverage directories.
- `backend/services/` contains unrelated capabilities and many large root-level `*_service.py` modules.
- Tests rely on widespread `sys.path` mutation, indicating unclear Python package boundaries.
- HTTP handling, business orchestration, persistence, integrations, and infrastructure concerns are mixed.
- Several core backend and frontend modules exceed 1,000 lines, but behavior-preserving organization must precede large-file decomposition.

## Target Backend Layers

```text
backend/
├── app.py
├── api/
│   ├── app_factory.py
│   ├── routes/
│   ├── schemas/
│   └── errors.py
├── services/
│   ├── blog_generation/
│   ├── review/
│   ├── publishing/
│   ├── media/
│   ├── documents/
│   ├── scheduling/
│   ├── llm/
│   └── integrations/
├── repositories/
│   ├── database/
│   ├── documents/
│   └── tasks/
├── models/
├── infrastructure/
│   ├── config/
│   ├── database/
│   ├── logging/
│   └── prompts/
├── shared/
└── tests/
```

This is a technical-layer architecture. The `services` layer is subdivided by business capability so it does not remain a catch-all directory.

## Dependency Rules

```text
api -> services -> repositories / integrations -> infrastructure
                  \-> models / shared
```

- `api` handles HTTP concerns, validation, and response conversion only.
- `services` owns use cases and orchestration.
- A service capability may use another capability only through its public package interface.
- `repositories` owns persistence and does not contain business rules.
- `models` contains stable data structures without framework dependencies.
- `infrastructure` owns configuration, database connections, logging, and prompt loading.
- `shared` is limited to genuinely cross-cutting, business-neutral code.
- Services must not import routes or Flask application objects.
- New large root-level files under `backend/services/` are prohibited.

## Repository Runtime Layout

Generated state will converge on one ignored root:

```text
var/
├── logs/
├── outputs/
├── uploads/
├── cache/
└── screenshots/
```

A centralized path configuration will be introduced before changing defaults. During the compatibility period, old locations remain readable and existing user data is not moved automatically.

## Compatibility Strategy

1. Create the new package or path boundary.
2. Move one capability without changing behavior.
3. Keep the old module as a thin import-forwarding compatibility layer.
4. Add tests for both the new import and the old import.
5. Verify backend CI, service startup, and affected E2E workflows.
6. Migrate callers in later PRs.
7. Remove old paths only in a dedicated cleanup PR after repository-wide usage checks.

Compatibility modules may re-export symbols but must not duplicate implementation.

## Pull Request Sequence

1. Remove and ignore repository-local UI/UX tool bundles while preserving `.github/`.
2. Introduce centralized runtime path configuration and the ignored `var/` layout.
3. Establish `repositories`, `models`, `shared`, and infrastructure package boundaries.
4. Migrate LLM services with old-import compatibility.
5. Migrate scheduling and task services.
6. Migrate media services and external media clients.
7. Migrate document and publishing services.
8. Normalize the API layer without changing URLs or response contracts.
9. Migrate review and blog-generation services last.
10. Remove proven-unused compatibility layers and eliminate `sys.path` mutations.

Large-file decomposition is intentionally separate from package moves. A migration PR may relocate code or introduce adapters, but it must not also redesign business behavior.

## Verification Gates

Every PR must:

- update `CHANGELOG.md`;
- contain one coherent structural boundary;
- pass `git diff --check`;
- pass relevant focused tests;
- pass the full non-LLM Python 3.10, 3.11, and 3.12 CI matrix when backend imports change;
- pass frontend CI when shared workflows or frontend paths change;
- verify Flask startup and `/health` when application wiring changes;
- run affected browser E2E cases when user workflows change;
- avoid generated logs, outputs, coverage, screenshots, caches, or uploads.

## Explicit Non-Goals

- No nested `vibe-blog/` project directory.
- No simultaneous Flask lifecycle or Docker/Nginx rewrite.
- No API contract changes during structural migration.
- No removal of `.github/` or its workflows.
- No automatic migration or deletion of user-generated runtime data.
