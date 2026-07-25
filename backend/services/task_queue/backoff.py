"""Compatibility alias for :mod:`services.scheduling.backoff`."""

import sys

from services.scheduling import backoff as _implementation

sys.modules[__name__] = _implementation
