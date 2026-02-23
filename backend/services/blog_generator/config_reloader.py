"""
Configuration hot-reload service -- reload workflow and agent configs at runtime
without restarting the service.

Thread-safe config cache with versioned reload support.
"""
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigReloader:
    """Thread-safe configuration hot-reload manager."""

    def __init__(self, config_dir: str = ""):
        self._lock = threading.Lock()
        self._config_dir = Path(config_dir) if config_dir else None
        self._cache: Dict[str, Any] = {}
        self._version: int = 0

    @property
    def version(self) -> int:
        return self._version

    def load_config(self, name: str, loader_fn) -> Any:
        """Load a config value (cached after first call)."""
        with self._lock:
            if name in self._cache:
                return self._cache[name]
            value = loader_fn()
            self._cache[name] = value
            return value

    def reload(self, name: str, loader_fn) -> bool:
        """Hot-reload a specific config. Returns True on success."""
        with self._lock:
            old = self._cache.get(name)
            try:
                new_value = loader_fn()
                self._cache[name] = new_value
                self._version += 1
                logger.info(f"Config '{name}' reloaded (v{self._version})")
                return True
            except Exception as e:
                logger.warning(f"Config reload failed for '{name}', keeping old: {e}")
                if old is not None:
                    self._cache[name] = old
                return False

    def reload_all(self, loaders: Dict[str, Any]) -> Dict[str, bool]:
        """Batch-reload multiple configs. Returns per-key success map."""
        results = {}
        for name, loader_fn in loaders.items():
            results[name] = self.reload(name, loader_fn)
        return results

    def get(self, name: str) -> Optional[Any]:
        """Get a cached config value, or None if not loaded."""
        with self._lock:
            return self._cache.get(name)

    def clear(self):
        """Clear all cached configs and reset version."""
        with self._lock:
            self._cache.clear()
            self._version = 0
