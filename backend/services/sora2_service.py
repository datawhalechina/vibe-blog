"""Compatibility alias for :mod:`services.media.sora2_service`."""

import sys

from .media import sora2_service as _implementation

sys.modules[__name__] = _implementation
