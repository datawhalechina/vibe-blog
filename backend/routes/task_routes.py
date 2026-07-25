"""Compatibility alias for :mod:`api.routes.task_routes`."""
import sys
from api.routes import task_routes as _implementation
sys.modules[__name__] = _implementation
