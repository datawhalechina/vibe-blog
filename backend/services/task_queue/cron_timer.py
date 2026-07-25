"""Compatibility alias for :mod:`services.scheduling.cron_timer`."""

import sys

from services.scheduling import cron_timer as _implementation

sys.modules[__name__] = _implementation
