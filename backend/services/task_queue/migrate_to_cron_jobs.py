"""Compatibility alias for :mod:`repositories.tasks.migrate_to_cron_jobs`."""

import sys

from repositories.tasks import migrate_to_cron_jobs as _implementation

sys.modules[__name__] = _implementation
