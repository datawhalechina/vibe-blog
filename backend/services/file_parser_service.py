"""Compatibility alias for :mod:`services.documents.file_parser_service`."""

import sys

from .documents import file_parser_service as _implementation

sys.modules[__name__] = _implementation
