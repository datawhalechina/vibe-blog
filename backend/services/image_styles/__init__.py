"""Compatibility alias for :mod:`services.media.image_styles`."""

import sys

from services.media import image_styles as _implementation
from services.media.image_styles import manager as _manager
from services.media.image_styles import type_signals as _type_signals

sys.modules[f"{__name__}.manager"] = _manager
sys.modules[f"{__name__}.type_signals"] = _type_signals
sys.modules[__name__] = _implementation
