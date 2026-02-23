"""TDD 测试 — 1003.22 会话生命周期管理"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.session_lifecycle import (
    SessionLifecycleManager, SessionStatus, SessionType, Session,
)

@pytest.fixture
def mgr():
    return SessionLifecycleManager()  # in-memory

class TestCreate:
    def test_creates_session(self, mgr):
        s = mgr.create(SessionType.BLOG_GENERATE, "Test Blog")
        assert s.session_id.startswith("sess_")
        assert s.session_type == SessionType.BLOG_GENERATE
        assert s.status == SessionStatus.CREATED

    def test_title_truncated(self, mgr):
        s = mgr.create(SessionType.BLOG_GENERATE, "x" * 200)
        assert len(s.title) <= 120

    def test_unique_ids(self, mgr):
        s1 = mgr.create(SessionType.BLOG_GENERATE, "A")
        s2 = mgr.create(SessionType.BLOG_GENERATE, "B")
        assert s1.session_id != s2.session_id

class TestGet:
    def test_get_existing(self, mgr):
        s = mgr.create(SessionType.BLOG_GENERATE, "Test")
        found = mgr.get(s.session_id)
        assert found is not None
        assert found.title == "Test"

    def test_get_nonexistent(self, mgr):
        assert mgr.get("nope") is None

class TestList:
    def test_list_all(self, mgr):
        mgr.create(SessionType.BLOG_GENERATE, "A")
        mgr.create(SessionType.XHS, "B")
        assert len(mgr.list_sessions()) == 2

    def test_filter_by_type(self, mgr):
        mgr.create(SessionType.BLOG_GENERATE, "A")
        mgr.create(SessionType.XHS, "B")
        result = mgr.list_sessions(session_type=SessionType.XHS)
        assert len(result) == 1
        assert result[0].session_type == SessionType.XHS

class TestUpdateStatus:
    def test_update(self, mgr):
        s = mgr.create(SessionType.BLOG_GENERATE, "Test")
        updated = mgr.update_status(s.session_id, SessionStatus.RUNNING)
        assert updated.status == SessionStatus.RUNNING

    def test_update_nonexistent(self, mgr):
        assert mgr.update_status("nope", SessionStatus.RUNNING) is None

class TestDelete:
    def test_delete_existing(self, mgr):
        s = mgr.create(SessionType.BLOG_GENERATE, "Test")
        assert mgr.delete(s.session_id) is True
        assert mgr.get(s.session_id) is None

    def test_delete_nonexistent(self, mgr):
        assert mgr.delete("nope") is False

class TestCapacity:
    def test_enforce_capacity(self, mgr):
        mgr.MAX_SESSIONS = 5
        for i in range(8):
            mgr.create(SessionType.BLOG_GENERATE, f"S{i}")
        assert len(mgr.list_sessions(limit=100)) <= 5

class TestMetadata:
    def test_metadata_stored(self, mgr):
        s = mgr.create(SessionType.BLOG_GENERATE, "Test", source="api")
        found = mgr.get(s.session_id)
        assert found.metadata.get("source") == "api"
