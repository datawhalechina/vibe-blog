"""Compatibility alias for :mod:`services.scheduling.cron_scheduler`."""

import sys

from services.scheduling import cron_scheduler as _implementation

sys.modules[__name__] = _implementation
