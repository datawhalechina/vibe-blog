# Testing Documentation Organization Design

## Goal

Keep the repository root focused on project entry points while preserving an accurate, discoverable testing guide and a valid Codecov configuration.

## Decisions

1. Replace the stale root `TESTING.md` with `docs/testing/README.md`.
2. Rewrite the guide from current commands and configuration instead of carrying forward static coverage snapshots.
3. Delete `TESTING_IMPLEMENTATION_SUMMARY.md`; it is a dated implementation report whose historical value is already covered by Git history and `CHANGELOG.md`.
4. Move `codecov.yml` to `.github/codecov.yml`, a location supported by Codecov.
5. Correct the invalid Codecov status layout, keep only flag-scoped project gates, and align them with the thresholds actually enforced by the repository: frontend 50%, backend 20%.
6. Link the new testing guide from the root README.
7. Ensure changes to `.github/codecov.yml` trigger both frontend and backend test workflows.

## Resulting Layout

```text
.github/
├── codecov.yml
└── workflows/
    ├── build-frontend.yml
    ├── test-backend.yml
    └── test-frontend.yml

docs/
├── testing/
│   └── README.md
└── plans/
```

## Validation

- Validate `.github/codecov.yml` with the official Codecov validation endpoint.
- Parse the YAML locally.
- Confirm the backend Codecov flag covers services, routes, utilities, and the app entry point used by pytest coverage.
- Check that stale placeholders and root-document references are gone.
- Check Markdown links and Git whitespace.
- Run the existing frontend and backend test workflows through the new path filters.
