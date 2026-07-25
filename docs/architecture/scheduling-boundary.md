# Scheduling Boundary

Queue and scheduling code is split by responsibility:

```text
backend/
├── models/scheduling.py                 # Pydantic data contracts
├── repositories/tasks/                  # SQLite persistence and migrations
└── services/scheduling/                  # Queue, cron, and scheduling orchestration
```

Application code should import orchestration from `services.scheduling`, data
contracts from `models.scheduling`, and persistence only when direct repository
access is required:

```python
from models.scheduling import BlogTask
from repositories.tasks import TaskDB
from services.scheduling import TaskQueueManager
```

The dependency direction is:

```text
api/routes -> services.scheduling -> repositories.tasks -> models.scheduling
```

## Compatibility

Existing `services.task_queue` imports remain valid. Its submodules alias the new
module objects, preserving class identity, module globals, and existing patch
targets. New production code must use the new package paths; the aliases exist
only to provide a gradual migration window.
