# Repository Tooling Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stop tracking repository-local UI/UX tool bundles while preserving GitHub Actions and application behavior.

**Architecture:** Remove only `.shared/ui-ux-pro-max/` and `.windsurf/skills/`, add exact ignore rules, and retain `.github/` and all other paths.

**Tech Stack:** Git, `.gitignore`, GitHub Actions

---

### Task 1: Capture the tracking baseline

**Files:**
- Read: `.shared/ui-ux-pro-max/**`
- Read: `.windsurf/skills/**`
- Read: `.github/workflows/**`

1. Count tracked files in all three locations.
2. Confirm application code does not import or execute either tool bundle.

### Task 2: Remove and ignore local tool bundles

**Files:**
- Modify: `.gitignore`
- Delete: `.shared/ui-ux-pro-max/**`
- Delete: `.windsurf/skills/**`

1. Add exact ignore rules for the two directories.
2. Remove their tracked files.
3. Do not ignore `.shared/`, `.windsurf/`, or `.github/` broadly.

### Task 3: Record and verify the cleanup

**Files:**
- Modify: `CHANGELOG.md`

1. Add a 2026-07-21 Changed entry.
2. Verify both removed paths have zero tracked files and are ignored.
3. Verify the three GitHub workflow files remain tracked and unchanged.
4. Run `git diff --check` and review the final file list.
5. Commit, push, and open a focused PR.
