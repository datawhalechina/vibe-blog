"""Compatibility alias for :mod:`services.publishing.oss_service`."""

import sys

from .publishing import oss_service as _implementation

sys.modules[__name__] = _implementation
