"""Compatibility alias for :mod:`services.llm.service`."""

import sys

from .llm import service as _implementation

sys.modules[__name__] = _implementation
