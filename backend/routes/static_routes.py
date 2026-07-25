"""Compatibility alias for :mod:`api.routes.static_routes`."""
import sys
from api.routes import static_routes as _implementation
sys.modules[__name__] = _implementation
