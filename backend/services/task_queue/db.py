"""Compatibility alias for :mod:`repositories.tasks.db`."""

import sys

from repositories.tasks import db as _implementation

sys.modules[__name__] = _implementation
