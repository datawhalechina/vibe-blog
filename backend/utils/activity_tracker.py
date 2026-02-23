"""
Dashboard activity tracking -- record and query user activity history.

Supports multiple activity modules: blog, chat, transform, publish, research.
"""
import json
import uuid
from collections import Counter
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class ActivityType(str, Enum):
    BLOG = "blog"
    CHAT = "chat"
    TRANSFORM = "transform"
    PUBLISH = "publish"
    RESEARCH = "research"


class ActivityTracker:
    """Activity history manager with optional file persistence."""

    MAX_ENTRIES = 200

    def __init__(self, storage_path: str = ""):
        self._path = Path(storage_path) if storage_path else None
        self._entries: List[dict] = []
        if self._path and self._path.exists():
            self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._entries = []

    def _save(self):
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)

    def add_entry(self, activity_type: str, title: str,
                  summary: str = "", metadata: Optional[dict] = None) -> dict:
        """Add a new activity entry and return it."""
        entry = {
            "id": str(uuid.uuid4())[:8],
            "type": activity_type,
            "title": title,
            "summary": summary,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        self._entries.append(entry)
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[-self.MAX_ENTRIES:]
        self._save()
        return entry

    def get_recent(self, limit: int = 20, activity_type: str = "") -> List[dict]:
        """Return recent entries in reverse chronological order."""
        entries = self._entries
        if activity_type:
            entries = [e for e in entries if e["type"] == activity_type]
        return list(reversed(entries[-limit:]))

    def get_entry(self, entry_id: str) -> Optional[dict]:
        """Find a specific entry by ID."""
        for e in self._entries:
            if e["id"] == entry_id:
                return e
        return None

    def get_stats(self) -> dict:
        """Return total count and breakdown by type."""
        type_counts = Counter(e["type"] for e in self._entries)
        return {
            "total": len(self._entries),
            "by_type": dict(type_counts),
        }

    def clear(self):
        """Remove all entries and persist."""
        self._entries.clear()
        self._save()
