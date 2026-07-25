"""Compatibility alias for :mod:`api.routes.queue_routes`."""
import sys
from api.routes import queue_routes as _implementation
sys.modules[__name__] = _implementation
