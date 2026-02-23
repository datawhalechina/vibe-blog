"""Tests for ConfigReloader — config hot-reload service."""
import sys
import os
import threading
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.config_reloader import ConfigReloader


class TestConfigReloader:
    """Unit tests for ConfigReloader."""

    def test_load_config_caches(self):
        """load_config calls loader only once for the same key."""
        reloader = ConfigReloader()
        loader = MagicMock(return_value={"key": "value"})

        reloader.load_config("workflow", loader)
        reloader.load_config("workflow", loader)

        loader.assert_called_once()

    def test_load_config_returns_value(self):
        """load_config returns the value produced by loader_fn."""
        reloader = ConfigReloader()
        loader = MagicMock(return_value={"model": "gpt-4"})

        result = reloader.load_config("agent", loader)

        assert result == {"model": "gpt-4"}

    def test_reload_success(self):
        """reload updates the cached value."""
        reloader = ConfigReloader()
        reloader.load_config("wf", MagicMock(return_value="old"))

        new_loader = MagicMock(return_value="new")
        ok = reloader.reload("wf", new_loader)

        assert ok is True
        assert reloader.get("wf") == "new"

    def test_reload_failure_keeps_old(self):
        """reload with a failing loader keeps the previous value."""
        reloader = ConfigReloader()
        reloader.load_config("wf", MagicMock(return_value="old"))

        bad_loader = MagicMock(side_effect=RuntimeError("boom"))
        ok = reloader.reload("wf", bad_loader)

        assert ok is False
        assert reloader.get("wf") == "old"

    def test_reload_increments_version(self):
        """Each successful reload increments version by 1."""
        reloader = ConfigReloader()
        assert reloader.version == 0

        reloader.reload("a", MagicMock(return_value=1))
        assert reloader.version == 1

        reloader.reload("b", MagicMock(return_value=2))
        assert reloader.version == 2

    def test_reload_all(self):
        """reload_all reloads multiple configs and returns per-key results."""
        reloader = ConfigReloader()
        reloader.load_config("x", MagicMock(return_value="x0"))
        reloader.load_config("y", MagicMock(return_value="y0"))

        loaders = {
            "x": MagicMock(return_value="x1"),
            "y": MagicMock(side_effect=ValueError("fail")),
        }
        results = reloader.reload_all(loaders)

        assert results == {"x": True, "y": False}
        assert reloader.get("x") == "x1"
        assert reloader.get("y") == "y0"  # kept old

    def test_get_returns_cached(self):
        """get returns a previously loaded config."""
        reloader = ConfigReloader()
        reloader.load_config("k", MagicMock(return_value=42))

        assert reloader.get("k") == 42

    def test_get_returns_none_for_missing(self):
        """get returns None for an unknown key."""
        reloader = ConfigReloader()
        assert reloader.get("nonexistent") is None

    def test_clear_resets(self):
        """clear removes all cached configs and resets version."""
        reloader = ConfigReloader()
        reloader.load_config("a", MagicMock(return_value=1))
        reloader.reload("a", MagicMock(return_value=2))
        assert reloader.version == 1

        reloader.clear()

        assert reloader.get("a") is None
        assert reloader.version == 0

    def test_thread_safety(self):
        """Concurrent loads don't corrupt state."""
        reloader = ConfigReloader()
        errors = []

        def worker(name: str):
            try:
                for i in range(100):
                    reloader.load_config(f"{name}_{i}", lambda v=i: v)
                    reloader.reload(f"{name}_{i}", lambda v=i + 1000: v)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"t{t}",)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # Each thread wrote 100 keys, all should be present
        for t in range(4):
            for i in range(100):
                assert reloader.get(f"t{t}_{i}") is not None
