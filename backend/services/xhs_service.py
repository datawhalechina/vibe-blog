"""Compatibility alias for :mod:`services.publishing.xhs_service`."""

import sys

from .publishing import xhs_service as _implementation

sys.modules[__name__] = _implementation
