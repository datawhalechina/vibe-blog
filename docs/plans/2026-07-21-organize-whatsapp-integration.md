# Organize WhatsApp Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the standalone WhatsApp gateway out of the repository root into the integrations boundary.

**Architecture:** Preserve the gateway as an independently installable Node.js package under `integrations/whatsapp-gateway/`. Update the local launcher to resolve the new path while keeping the default-disabled and opt-in authentication behavior unchanged.

**Tech Stack:** Node.js 20, Bash, Baileys

---

### Task 1: Move the gateway package

1. Move all tracked `whatsapp-gateway/` files into `integrations/whatsapp-gateway/`.
2. Preserve package and lock file contents.
3. Preserve local ignore rules for authentication state and dependencies.

### Task 2: Update the local launcher

1. Update `WHATSAPP_DIR` in `docker/start-local.sh`.
2. Ensure printed authentication guidance uses the new location through the resolved variable.
3. Protect the ignored legacy `store/` path and migrate it when the new location has no local data.
4. Search for stale root-level gateway references.

### Task 3: Verify and publish

1. Run `npm ci` in the new package directory.
2. Run Node syntax checks for both source files and Bash syntax checks for the launcher.
3. Verify default-disabled startup path behavior without contacting WhatsApp.
4. Update `CHANGELOG.md`, review the diff, and create a standalone PR.
