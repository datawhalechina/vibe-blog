"""Compatibility alias for :mod:`services.documents.knowledge_service`."""

import sys

from .documents import knowledge_service as _implementation

sys.modules[__name__] = _implementation
