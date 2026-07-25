# Backend Package Boundaries

VibeBlog evolves toward the following dependency direction:

```text
api -> services -> repositories -> infrastructure
                 -> models
                 -> shared
```

The packages introduced in this baseline are intentionally empty. Capability
implementations move in later focused pull requests; this PR only reserves the
ownership boundaries and makes them enforceable.

## Responsibilities

| Package | Owns | Must not own |
| --- | --- | --- |
| `api` | HTTP parsing, validation, response conversion | Business workflows or persistence |
| `services` | Use cases and business orchestration | Flask routes or database connection setup |
| `repositories` | Persistence interfaces and resource-specific storage | HTTP handling or business rules |
| `models` | Stable framework-neutral data structures | Flask, services, repositories, or infrastructure |
| `infrastructure` | Configuration, connections, logging, prompts | API or business orchestration |
| `shared` | Small business-neutral cross-cutting helpers | Feature-specific workflows or infrastructure |

## Enforcement

`backend/tests/architecture/test_package_boundaries.py` parses Python imports
with the standard `ast` module. It prevents lower layers from importing upper
layers while later migration PRs populate the packages. Relative imports inside
the same boundary remain allowed.

Two existing blog-generation modules that access Flask `current_app` are
recorded in an explicit legacy allowlist. The test rejects any new Flask access;
the existing entries are removed when the blog-generation boundary migrates.

Legacy modules are not moved by this baseline. Each later PR must move one
capability, retain a thin old-import forwarding module, and extend the boundary
tests when that capability becomes governed by the new package.
