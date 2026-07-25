"""Compatibility alias for :mod:`services.media.image_styles.type_signals`."""

import sys

from services.media.image_styles import type_signals as _implementation

sys.modules[__name__] = _implementation
