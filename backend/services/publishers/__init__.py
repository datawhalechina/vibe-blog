"""Compatibility alias for :mod:`services.publishing.publishers`."""

import sys

from services.publishing import publishers as _implementation
from services.publishing.publishers import publisher as _publisher
from services.publishing.publishers import workflow_engine as _workflow_engine

sys.modules[f"{__name__}.publisher"] = _publisher
sys.modules[f"{__name__}.workflow_engine"] = _workflow_engine
sys.modules[__name__] = _implementation
