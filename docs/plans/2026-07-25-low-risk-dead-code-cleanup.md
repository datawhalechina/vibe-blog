# Low-Risk Dead Code Cleanup Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** Remove one proven-unreferenced Vue component without changing application behavior.

**Architecture:** Treat `frontend/src/main.ts` and `frontend/src/router/index.ts` as the frontend roots, then confirm that no production source, test, or Vite configuration imports the candidate. Delete only the isolated file and verify the existing application suite and production bundle.

**Tech Stack:** Vue 3, TypeScript, Vite, Vitest

---

### Task 1: Remove the isolated result card

**Files:**
- Create: `frontend/__tests__/unit/noOrphanRootComponents.test.ts`
- Delete: `frontend/src/components/ResultCard.vue`

**Step 1: Confirm the component has no consumers**

Run:

```bash
rg -n "ResultCard|components/ResultCard|<result-card|<ResultCard" frontend/src frontend/__tests__ frontend/vite.config.ts
```

Expected: no consumers match. Confirm the candidate itself exists separately with `test -f frontend/src/components/ResultCard.vue`.

**Step 2: Add and verify the reachability regression test**

Add a test that resolves static and dynamic Vue imports, then reports top-level `src/components/*.vue` files that are neither imported nor explicitly awaiting a separate audit. Run it with `ResultCard.vue` present.

Expected: FAIL with `ResultCard.vue` as the only orphan component.

**Step 3: Delete the component**

Delete `frontend/src/components/ResultCard.vue`; no import or barrel export requires adjustment.

**Step 4: Confirm the regression test turns green**

Run: `cd frontend && npm test -- --run __tests__/unit/noOrphanRootComponents.test.ts`

Expected: the focused architecture test passes.

**Step 5: Confirm no dangling references remain**

Run the Step 1 command again.

Expected: no matches.

**Step 6: Run frontend tests**

Run: `cd frontend && npm test -- --run`

Expected: all discovered Vitest tests pass.

**Step 7: Build the production frontend**

Run: `cd frontend && npm run build`

Expected: Vite exits successfully and emits the production bundle.

If the existing ignored `frontend/dist` directory is not writable, preserve it and run `npm run build -- --outDir /tmp/vibe-blog-dist` instead.

**Step 8: Review the cleanup diff**

Run: `git diff -- frontend/src/components/ResultCard.vue docs/plans/2026-07-25-low-risk-dead-code-cleanup-design.md docs/plans/2026-07-25-low-risk-dead-code-cleanup.md`

Expected: one component deletion and the two scoped planning records, with no unrelated edits.
