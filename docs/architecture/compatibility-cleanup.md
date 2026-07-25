# Compatibility Cleanup Audit

Backend tests use the repository's pytest configuration for imports:

```ini
[pytest]
pythonpath = .
```

Test modules must not mutate `sys.path`. An AST architecture test enforces this
rule for `backend/conftest.py` and every Python file under `backend/tests/`.

## Compatibility Alias Decision

The legacy route and service aliases introduced by the incremental migration are
not removed in this phase. Repository tests and patch targets still consume
paths including `routes.*`, `services.llm_service`, `services.task_queue.*`, and
the previous media, document, and publishing modules.

Removing those aliases now would violate the compatibility window. They may be
deleted only after downstream callers and legacy tests have migrated, the
deprecation has been announced, and a repository-wide scan returns no consumers.

Standalone diagnostic scripts and `backend/__init__.py` retain their existing
path bootstrap behavior because they run outside pytest. Converting those entry
points requires a separate packaging and invocation migration.
