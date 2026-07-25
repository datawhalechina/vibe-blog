"""Compatibility alias for :mod:`services.scheduling.manager`."""

import sys

from services.scheduling import manager as _implementation

sys.modules[__name__] = _implementation
