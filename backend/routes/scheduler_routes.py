"""Compatibility alias for :mod:`api.routes.scheduler_routes`."""
import sys
from api.routes import scheduler_routes as _implementation
sys.modules[__name__] = _implementation
