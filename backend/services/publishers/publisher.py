"""Compatibility alias for :mod:`services.publishing.publishers.publisher`."""

import sys

from services.publishing.publishers import publisher as _implementation

sys.modules[__name__] = _implementation
