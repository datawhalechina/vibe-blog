# Runtime Paths

VibeBlog runtime state will converge on a single repository-level `var/`
directory:

```text
var/
├── logs/
├── outputs/
├── uploads/
├── cache/
└── screenshots/
```

The `infrastructure.paths.RuntimePaths` value object defines this target
layout. By default, it resolves `var/` relative to the repository root.
Set `VIBE_RUNTIME_DIR` to use another root:

```bash
VIBE_RUNTIME_DIR=/srv/vibe-blog/state
```

A relative override is resolved from the repository root. An absolute override
is preserved. Empty and whitespace-only values are treated as unset and fall
back to the repository `var/` directory.

## Compatibility Contract

- Resolving paths does not create directories.
- New runtime writes use the repository-level `var/` layout.
- Existing logs, outputs, uploads, caches, and screenshots are not moved or
  deleted automatically.
- `/outputs/*` URLs are unchanged and read from `var/outputs` first, then the
  legacy `backend/outputs` directory.
- Existing Markdown files stored under `backend/outputs` remain editable.
- E2E log analysis reads the new locations first and falls back to legacy logs
  and screenshots.
- Cache data is disposable and is recreated under `var/cache`; no cache files
  are copied during migration.
- The repository-level `var/` directory is ignored by Git.

## Explicit Overrides

`VIBE_RUNTIME_DIR` changes the complete runtime root. Existing deployment
variables remain supported for deployments that mount separate directories:

| Variable | Target |
| --- | --- |
| `OUTPUT_FOLDER` | Generated Markdown, images, covers, and videos |
| `UPLOAD_FOLDER` | Uploaded source documents |
| `CACHE_DIR` | Disk-backed cache |
| `SCREENSHOT_DIR` | Browser and E2E screenshots |
| `LOG_DIR` | Application log directory |
| `BLOG_LOGS_DIR` | Structured per-task logs |

Docker Compose mounts the complete repository `var/` directory at `/app/var`.
