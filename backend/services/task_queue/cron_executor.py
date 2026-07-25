"""Compatibility alias for :mod:`services.scheduling.cron_executor`."""

import sys

from services.scheduling import cron_executor as _implementation

sys.modules[__name__] = _implementation
