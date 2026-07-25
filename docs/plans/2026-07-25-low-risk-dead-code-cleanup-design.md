# Low-Risk Dead Code Cleanup Design

## Scope

Remove only production files that have no static or dynamic references from application entry points, routes, source code, tests, or build configuration. Do not remove deprecated static pages while Flask routes still serve them, and do not bulk-fix unused Python imports because some are optional-dependency probes.

## First Cleanup

Delete `frontend/src/components/ResultCard.vue`. Repository-wide searches find no consumers, and its Git history shows that it was previously removed on a later development line before returning through branch history.

## Verification

Add a generic architecture test that rejects unreviewed top-level Vue components with no production import. Keep existing candidates outside this cleanup on an explicit audit allowlist. Demonstrate the test's RED state with `ResultCard.vue` present, delete the orphan for GREEN, then run the complete frontend unit test suite and create a production frontend build. Review the final diff to ensure no unrelated user changes are included.
