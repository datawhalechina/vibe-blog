"""Compatibility alias for :mod:`services.publishing.publishers.workflow_engine`."""

import sys

from services.publishing.publishers import workflow_engine as _implementation

sys.modules[__name__] = _implementation
