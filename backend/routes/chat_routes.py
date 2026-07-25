"""Compatibility alias for :mod:`api.routes.chat_routes`."""
import sys
from api.routes import chat_routes as _implementation
sys.modules[__name__] = _implementation
