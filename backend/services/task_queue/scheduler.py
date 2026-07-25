"""Compatibility alias for :mod:`services.scheduling.scheduler`."""

import sys

from services.scheduling import scheduler as _implementation

sys.modules[__name__] = _implementation
