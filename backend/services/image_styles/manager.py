"""Compatibility alias for :mod:`services.media.image_styles.manager`."""

import sys

from services.media.image_styles import manager as _implementation

sys.modules[__name__] = _implementation
