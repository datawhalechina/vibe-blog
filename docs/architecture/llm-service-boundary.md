# LLM Service Boundary

LLM provider factories and model lifecycle management live under one capability
package:

```text
backend/services/llm/
├── __init__.py
├── factory.py
└── service.py
```

Use the public package for normal callers:

```python
from services.llm import LLMService, get_llm_service, init_llm_service
```

Internal helpers remain available from `services.llm.service` while callers are
gradually simplified.

## Compatibility

`services.llm_service` and `services.llm_factory` remain valid. Each legacy
module aliases the corresponding new module object instead of copying symbols.
This preserves:

- singleton and module-global state;
- private helper imports used by existing integrations;
- tests and extensions that patch module globals such as `ChatOpenAI`;
- object identity between old and new import paths.

The aliases can be removed only after a repository-wide usage scan and an
announced compatibility cleanup.
