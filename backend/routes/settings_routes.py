"""Compatibility alias for :mod:`api.routes.settings_routes`."""
import sys
from api.routes import settings_routes as _implementation
sys.modules[__name__] = _implementation
