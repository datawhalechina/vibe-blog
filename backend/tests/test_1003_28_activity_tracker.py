"""Tests for ActivityTracker — Dashboard activity tracking."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.activity_tracker import ActivityTracker, ActivityType


class TestAddEntry:
    def test_add_entry(self):
        tracker = ActivityTracker()
        entry = tracker.add_entry("blog", "My Post", summary="A summary")
        assert entry["type"] == "blog"
        assert entry["title"] == "My Post"
        assert entry["summary"] == "A summary"
        assert "id" in entry
        assert "created_at" in entry
        assert entry["metadata"] == {}

    def test_add_entry_with_metadata(self):
        tracker = ActivityTracker()
        meta = {"word_count": 1500, "tags": ["ai", "python"]}
        entry = tracker.add_entry("chat", "Chat Session", metadata=meta)
        assert entry["metadata"] == meta
        assert entry["metadata"]["word_count"] == 1500


class TestGetRecent:
    def test_get_recent_default(self):
        tracker = ActivityTracker()
        e1 = tracker.add_entry("blog", "First")
        e2 = tracker.add_entry("chat", "Second")
        e3 = tracker.add_entry("blog", "Third")
        recent = tracker.get_recent()
        # Reverse chronological: newest first
        assert recent[0]["id"] == e3["id"]
        assert recent[1]["id"] == e2["id"]
        assert recent[2]["id"] == e1["id"]

    def test_get_recent_by_type(self):
        tracker = ActivityTracker()
        tracker.add_entry("blog", "Blog 1")
        tracker.add_entry("chat", "Chat 1")
        tracker.add_entry("blog", "Blog 2")
        recent = tracker.get_recent(activity_type="blog")
        assert len(recent) == 2
        assert all(e["type"] == "blog" for e in recent)

    def test_get_recent_limit(self):
        tracker = ActivityTracker()
        for i in range(10):
            tracker.add_entry("blog", f"Post {i}")
        recent = tracker.get_recent(limit=3)
        assert len(recent) == 3
        # Should be the 3 most recent, newest first
        assert recent[0]["title"] == "Post 9"
        assert recent[1]["title"] == "Post 8"
        assert recent[2]["title"] == "Post 7"


class TestGetEntry:
    def test_get_entry_by_id(self):
        tracker = ActivityTracker()
        entry = tracker.add_entry("blog", "Target Post")
        found = tracker.get_entry(entry["id"])
        assert found is not None
        assert found["title"] == "Target Post"

    def test_get_entry_not_found(self):
        tracker = ActivityTracker()
        tracker.add_entry("blog", "Some Post")
        assert tracker.get_entry("nonexistent") is None


class TestGetStats:
    def test_get_stats(self):
        tracker = ActivityTracker()
        tracker.add_entry("blog", "B1")
        tracker.add_entry("blog", "B2")
        tracker.add_entry("chat", "C1")
        tracker.add_entry("transform", "T1")
        stats = tracker.get_stats()
        assert stats["total"] == 4
        assert stats["by_type"]["blog"] == 2
        assert stats["by_type"]["chat"] == 1
        assert stats["by_type"]["transform"] == 1


class TestMaxEntries:
    def test_max_entries(self):
        tracker = ActivityTracker()
        for i in range(210):
            tracker.add_entry("blog", f"Post {i}")
        recent = tracker.get_recent(limit=300)
        # Internal list should be trimmed to 200
        assert len(tracker._entries) == 200
        # Oldest entries should be dropped
        assert tracker._entries[0]["title"] == "Post 10"


class TestPersistence:
    def test_persistence(self, tmp_path):
        filepath = str(tmp_path / "activity.json")
        tracker = ActivityTracker(storage_path=filepath)
        tracker.add_entry("blog", "Persisted Post", summary="saved")
        tracker.add_entry("chat", "Chat Entry")

        # Create a new tracker from the same file
        tracker2 = ActivityTracker(storage_path=filepath)
        assert len(tracker2._entries) == 2
        assert tracker2._entries[0]["title"] == "Persisted Post"
        assert tracker2._entries[1]["title"] == "Chat Entry"

        # Verify the file content
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2


class TestClear:
    def test_clear(self, tmp_path):
        filepath = str(tmp_path / "activity.json")
        tracker = ActivityTracker(storage_path=filepath)
        tracker.add_entry("blog", "To be cleared")
        tracker.add_entry("chat", "Also cleared")
        assert len(tracker._entries) == 2

        tracker.clear()
        assert len(tracker._entries) == 0

        # Verify persistence after clear
        tracker2 = ActivityTracker(storage_path=filepath)
        assert len(tracker2._entries) == 0
