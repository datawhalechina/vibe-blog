"""Compatibility alias for :mod:`models.scheduling`."""

import sys

from models import scheduling as _implementation

sys.modules[__name__] = _implementation
