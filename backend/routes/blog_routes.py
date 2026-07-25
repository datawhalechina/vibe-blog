"""Compatibility alias for :mod:`api.routes.blog_routes`."""
import sys
from api.routes import blog_routes as _implementation
sys.modules[__name__] = _implementation
