# Documents and Publishing Boundaries

Document processing and publishing integrations are grouped by capability:

```text
backend/services/
├── documents/
│   ├── book_scanner_service.py
│   ├── file_parser_service.py
│   └── knowledge_service.py
└── publishing/
    ├── oss_service.py
    ├── publishers/
    └── xhs_service.py
```

Use the package APIs for lifecycle and common service access:

```python
from services.documents import get_file_parser, get_knowledge_service
from services.publishing import Publisher, get_oss_service
```

## Compatibility

The previous top-level service modules and `services.publishers` package remain
module aliases. They preserve singleton state, class identity, and existing
patch targets while callers migrate to the new capability packages.
