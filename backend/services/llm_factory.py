"""Compatibility alias for :mod:`services.llm.factory`."""

import sys

from .llm import factory as _implementation

sys.modules[__name__] = _implementation
