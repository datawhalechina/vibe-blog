"""Compatibility alias for :mod:`services.media.image_service`."""

import sys

from .media import image_service as _implementation

sys.modules[__name__] = _implementation
