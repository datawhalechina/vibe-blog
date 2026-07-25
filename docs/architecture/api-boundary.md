# HTTP API Boundary

The Flask application factory and route modules live under `backend/api/`:

```text
backend/api/
├── app_factory.py
├── errors.py
├── routes/
└── schemas/
```

Application startup continues to use the stable package API:

```python
from api import create_app
```

New HTTP code belongs in `api/routes`, request and response contracts belong in
`api/schemas`, and shared HTTP error translation belongs in `api/errors`.
Business logic must remain in services rather than route modules.

## Compatibility

The previous `routes.*` modules remain aliases to `api.routes.*`. This preserves
Blueprint identity, test patch targets, and third-party imports. URL rules,
Blueprint names, and response contracts are unchanged by this migration.
