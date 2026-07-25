"""Compatibility alias for :mod:`services.documents.book_scanner_service`."""

import sys

from .documents import book_scanner_service as _implementation

sys.modules[__name__] = _implementation
