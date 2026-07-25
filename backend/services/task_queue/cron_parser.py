"""Compatibility alias for :mod:`services.scheduling.cron_parser`."""

import sys

from services.scheduling import cron_parser as _implementation

sys.modules[__name__] = _implementation
