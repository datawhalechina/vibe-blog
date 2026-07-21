# Deprecate vibe-reviewer Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove vibe-reviewer from active project documentation while preserving an explicit deprecation record.

**Architecture:** Remove promotional, roadmap, and detailed tree references from the Chinese README, retain runtime code unchanged, and create a centralized `docs/deprecated/` inventory. Archive the existing screenshots under the deprecated documentation namespace without modifying their bytes.

**Tech Stack:** Markdown, Git, PNG assets

---

### Task 1: Remove active documentation

1. Delete the vibe-reviewer feature introduction from `README.md`.
2. Remove it from the completed-feature table and detailed repository tree.
3. Keep the English README consistent with the new documentation directory structure.

### Task 2: Record the deprecation

1. Create `docs/deprecated/README.md` with status, date, former entry points, retained code, and removal policy.
2. Move the three historical screenshots into `docs/deprecated/assets/vibe-reviewer/` without changing their bytes.
3. Update `CHANGELOG.md`.

### Task 3: Verify and publish

1. Check all README image links and archived-image hashes.
2. Confirm active README content no longer advertises vibe-reviewer.
3. Review the diff and create a PR stacked on the documentation-assets PR.
