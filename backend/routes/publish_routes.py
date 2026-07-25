"""Compatibility alias for :mod:`api.routes.publish_routes`."""
import sys
from api.routes import publish_routes as _implementation
sys.modules[__name__] = _implementation
