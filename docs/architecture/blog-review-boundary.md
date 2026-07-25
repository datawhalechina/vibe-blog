# Blog Generation and Review Boundaries

External callers use two stable capability facades:

```text
backend/services/
├── blog_generation/    # generation, search, prompt, and summary API
└── review/             # reviewer agent and guideline API
```

Typical imports are:

```python
from services.blog_generation import get_blog_service, get_prompt_manager
from services.review import ReviewerAgent, get_guidelines
```

## Incremental Core Migration

The LangGraph implementation remains under `services/blog_generator` during
this phase. It contains many relative imports, module-level state, and existing
patch targets. Loading those files under a second package name would create
duplicate module objects and could split graph state or singleton services.

The new facades lazily return the original objects, so external dependencies can
stabilize first without changing workflow behavior. Moving the internal graph
package requires a separate migration with an import alias loader or a coordinated
breaking release; it is intentionally excluded from this low-regression PR.
