"""Thread-safe ownership of detached artist tasks."""

import threading


class ImageTaskRegistry:
    def __init__(self):
        self._tasks = {}
        self._lock = threading.Lock()

    def register(self, task_id, future, executor) -> None:
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Image task already registered: {task_id}")
            self._tasks[task_id] = (future, executor)

    def pop(self, task_id, *, timeout=None, default=None):
        with self._lock:
            task = self._tasks.pop(task_id, None)
        if task is None:
            return default
        future, executor = task
        try:
            if timeout is None:
                return future.result()
            return future.result(timeout=timeout)
        finally:
            executor.shutdown(wait=False)

    def discard(self, task_id) -> None:
        with self._lock:
            task = self._tasks.pop(task_id, None)
        if task is None:
            return
        future, executor = task
        try:
            future.cancel()
        finally:
            executor.shutdown(wait=False)
