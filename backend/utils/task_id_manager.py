"""
Unified Task ID Manager -- thread-safe task ID generation, status tracking, and auto-cleanup.
"""
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class TaskIDManager:
    """Thread-safe task ID manager (singleton)."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tasks: Dict[str, dict] = {}
                cls._instance._key_map: Dict[str, str] = {}
            return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        with cls._lock:
            cls._instance = None

    def generate(self, task_type: str = "blog", task_key: str = "") -> str:
        """Generate a task ID. Idempotent: same task_key returns same ID."""
        with self._lock:
            if task_key and task_key in self._key_map:
                return self._key_map[task_key]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            uid = str(uuid.uuid4())[:8]
            task_id = f"{task_type}_{ts}_{uid}"
            self._tasks[task_id] = {
                "task_type": task_type,
                "task_key": task_key,
                "created_at": datetime.now().isoformat(),
                "status": "running",
                "finished_at": None,
            }
            if task_key:
                self._key_map[task_key] = task_id
            return task_id

    def update_status(self, task_id: str, status: str) -> bool:
        """Update task status (running -> completed/error/cancelled)."""
        with self._lock:
            if task_id not in self._tasks:
                return False
            self._tasks[task_id]["status"] = status
            if status in ("completed", "error", "cancelled"):
                self._tasks[task_id]["finished_at"] = datetime.now().isoformat()
            return True

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get task info."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status: str = "") -> List[dict]:
        """List tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t["status"] == status]
            return tasks

    def cleanup(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0
        with self._lock:
            to_remove = []
            for tid, info in self._tasks.items():
                if info["status"] in ("completed", "error", "cancelled"):
                    if info.get("finished_at"):
                        finished = datetime.fromisoformat(info["finished_at"])
                        if finished < cutoff:
                            to_remove.append(tid)
            for tid in to_remove:
                task_key = self._tasks[tid].get("task_key", "")
                del self._tasks[tid]
                if task_key and task_key in self._key_map:
                    del self._key_map[task_key]
                removed += 1
        return removed
