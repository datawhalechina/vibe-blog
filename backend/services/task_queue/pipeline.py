"""Compatibility alias for :mod:`services.scheduling.pipeline`."""

import sys

from services.scheduling import pipeline as _implementation

sys.modules[__name__] = _implementation
