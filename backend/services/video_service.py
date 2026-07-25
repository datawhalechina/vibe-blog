"""Compatibility alias for :mod:`services.media.video_service`."""

import sys

from .media import video_service as _implementation

sys.modules[__name__] = _implementation
