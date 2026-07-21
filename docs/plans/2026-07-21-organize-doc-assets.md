# Organize Documentation Assets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move README-only images from the root `logo/` directory into categorized documentation assets.

**Architecture:** Preserve image bytes and filenames while grouping assets under `docs/assets/brand`, `screenshots`, `diagrams`, `examples`, and `community`. Update both maintained README files and verify every local image target exists after the move.

**Tech Stack:** Markdown, PNG assets, Git

---

### Task 1: Categorize documentation images

**Files:**
- Move: `logo/*.png` into categorized `docs/assets/` subdirectories

1. Classify each image by its current README role.
2. Move files without re-encoding or renaming them.
3. Confirm every moved file has an identical checksum.

### Task 2: Update documentation references

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `CHANGELOG.md`

1. Replace all `./logo/` links with categorized `./docs/assets/` links.
2. Update repository structure examples.
3. Record the documentation asset organization change.

### Task 3: Verify and publish

1. Parse local Markdown image references and assert every target exists.
2. Search for stale `logo/` references and confirm the root directory is gone.
3. Review the complete diff, push the branch, and create a focused PR.
