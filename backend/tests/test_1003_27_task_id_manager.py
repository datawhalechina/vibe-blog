"""
Tests for TaskIDManager — thread-safe task ID generation, status tracking, cleanup.
"""
import re
import sys
import os
import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.task_id_manager import TaskIDManager


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset TaskIDManager singleton before each test."""
    TaskIDManager.reset()
    yield
    TaskIDManager.reset()


class TestGenerate:
    def test_generate_format(self):
        """ID matches pattern {type}_{YYYYMMDD_HHMMSS}_{8-char-uuid}."""
        mgr = TaskIDManager()
        task_id = mgr.generate(task_type="blog")
        pattern = r"^blog_\d{8}_\d{6}_[a-f0-9]{8}$"
        assert re.match(pattern, task_id), f"ID '{task_id}' does not match expected pattern"

    def test_generate_idempotent(self):
        """Same task_key returns the same ID."""
        mgr = TaskIDManager()
        id1 = mgr.generate(task_type="blog", task_key="user123_topic456")
        id2 = mgr.generate(task_type="blog", task_key="user123_topic456")
        assert id1 == id2

    def test_generate_unique(self):
        """Different calls without key produce different IDs."""
        mgr = TaskIDManager()
        id1 = mgr.generate(task_type="blog")
        id2 = mgr.generate(task_type="blog")
        assert id1 != id2


class TestSingleton:
    def test_singleton(self):
        """Two instances are the same object."""
        mgr1 = TaskIDManager()
        mgr2 = TaskIDManager()
        assert mgr1 is mgr2


class TestUpdateStatus:
    def test_update_status(self):
        """Update from running to completed sets finished_at."""
        mgr = TaskIDManager()
        task_id = mgr.generate(task_type="blog")
        result = mgr.update_status(task_id, "completed")
        assert result is True
        task = mgr.get_task(task_id)
        assert task["status"] == "completed"
        assert task["finished_at"] is not None

    def test_update_nonexistent(self):
        """Returns False for unknown task_id."""
        mgr = TaskIDManager()
        result = mgr.update_status("nonexistent_id", "completed")
        assert result is False


class TestGetTask:
    def test_get_task(self):
        """Returns task info dict with expected keys."""
        mgr = TaskIDManager()
        task_id = mgr.generate(task_type="blog", task_key="mykey")
        task = mgr.get_task(task_id)
        assert task is not None
        assert task["task_type"] == "blog"
        assert task["task_key"] == "mykey"
        assert task["status"] == "running"
        assert task["finished_at"] is None

    def test_get_task_nonexistent(self):
        """Returns None for unknown task_id."""
        mgr = TaskIDManager()
        assert mgr.get_task("no_such_id") is None


class TestListTasks:
    def test_list_tasks(self):
        """List all tasks and filter by status."""
        mgr = TaskIDManager()
        id1 = mgr.generate(task_type="blog")
        id2 = mgr.generate(task_type="blog")
        mgr.update_status(id1, "completed")

        all_tasks = mgr.list_tasks()
        assert len(all_tasks) == 2

        running = mgr.list_tasks(status="running")
        assert len(running) == 1
        assert running[0]["status"] == "running"

        completed = mgr.list_tasks(status="completed")
        assert len(completed) == 1
        assert completed[0]["status"] == "completed"


class TestCleanup:
    def test_cleanup_removes_old(self):
        """Removes old completed tasks, keeps running ones."""
        mgr = TaskIDManager()
        id_running = mgr.generate(task_type="blog")
        id_old = mgr.generate(task_type="blog")
        mgr.update_status(id_old, "completed")

        # Manually backdate the finished_at to 48 hours ago
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        mgr._tasks[id_old]["finished_at"] = old_time

        removed = mgr.cleanup(max_age_hours=24)
        assert removed == 1
        assert mgr.get_task(id_old) is None
        assert mgr.get_task(id_running) is not None

    def test_cleanup_keeps_recent(self):
        """Completed tasks within max_age are kept."""
        mgr = TaskIDManager()
        task_id = mgr.generate(task_type="blog")
        mgr.update_status(task_id, "completed")
        # finished_at is now, well within 24 hours

        removed = mgr.cleanup(max_age_hours=24)
        assert removed == 0
        assert mgr.get_task(task_id) is not None
