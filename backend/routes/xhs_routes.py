"""Compatibility alias for :mod:`api.routes.xhs_routes`."""
import sys
from api.routes import xhs_routes as _implementation
sys.modules[__name__] = _implementation
