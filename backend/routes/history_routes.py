"""Compatibility alias for :mod:`api.routes.history_routes`."""
import sys
from api.routes import history_routes as _implementation
sys.modules[__name__] = _implementation
