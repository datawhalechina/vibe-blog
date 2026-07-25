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
- Existing runtime consumers keep their current paths in the foundation PR.
- Existing logs, outputs, uploads, caches, and screenshots are not moved or
  deleted automatically.
- Each consumer will migrate in a focused follow-up PR with an old-path read
  fallback where persisted data must remain accessible.
- The repository-level `var/` directory is ignored by Git.
