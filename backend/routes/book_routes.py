"""Compatibility alias for :mod:`api.routes.book_routes`."""
import sys
from api.routes import book_routes as _implementation
sys.modules[__name__] = _implementation
