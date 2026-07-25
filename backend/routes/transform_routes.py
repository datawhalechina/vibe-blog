"""Compatibility alias for :mod:`api.routes.transform_routes`."""
import sys
from api.routes import transform_routes as _implementation
sys.modules[__name__] = _implementation
