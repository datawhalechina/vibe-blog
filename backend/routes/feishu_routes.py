"""Compatibility alias for :mod:`api.routes.feishu_routes`."""
import sys
from api.routes import feishu_routes as _implementation
sys.modules[__name__] = _implementation
