# Organize English README Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the alternate English README out of the repository root while preserving navigation and every local link.

**Architecture:** Keep `README.md` as the GitHub repository entry point and place translated variants under `docs/i18n/`. Update links according to the new two-level depth without changing English documentation content.

**Tech Stack:** Markdown, Git

---

### Task 1: Move the English README

1. Move `README_EN.md` to `docs/i18n/README_EN.md`.
2. Update the root README language switch.
3. Rewrite relative links for the repository root, documentation assets, backend examples, testing guide, and deprecated inventory.

### Task 2: Verify documentation navigation

1. Check every local Markdown and image target from the moved file.
2. Confirm English-to-Chinese and Chinese-to-English navigation works.
3. Search for stale root-level `README_EN.md` references.

### Task 3: Review and publish

1. Update `CHANGELOG.md`.
2. Review the focused diff.
3. Push the branch and create a standalone PR.
