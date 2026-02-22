"""
TDD 测试 — 1003.09 笔记本管理服务 (NotebookService)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.notebook_service import NotebookService


@pytest.fixture
def svc():
    return NotebookService()  # in-memory SQLite


class TestCreateNotebook:
    def test_returns_valid_structure(self, svc):
        nb = svc.create_notebook("测试笔记本")
        assert "id" in nb
        assert nb["name"] == "测试笔记本"
        assert nb["color"] == "#3B82F6"
        assert nb["icon"] == "book"

    def test_generates_unique_id(self, svc):
        nb1 = svc.create_notebook("A")
        nb2 = svc.create_notebook("B")
        assert nb1["id"] != nb2["id"]

    def test_custom_color_and_icon(self, svc):
        nb = svc.create_notebook("X", color="#FF0000", icon="star")
        assert nb["color"] == "#FF0000"
        assert nb["icon"] == "star"


class TestListNotebooks:
    def test_empty(self, svc):
        assert svc.list_notebooks() == []

    def test_with_record_count(self, svc):
        nb = svc.create_notebook("NB")
        svc.add_record(nb["id"], "blog", "Title1")
        svc.add_record(nb["id"], "note", "Title2")
        lst = svc.list_notebooks()
        assert len(lst) == 1
        assert lst[0]["record_count"] == 2


class TestGetNotebook:
    def test_with_records(self, svc):
        nb = svc.create_notebook("NB")
        svc.add_record(nb["id"], "blog", "T1", content="hello")
        detail = svc.get_notebook(nb["id"])
        assert detail is not None
        assert len(detail["records"]) == 1
        assert detail["records"][0]["title"] == "T1"

    def test_not_found(self, svc):
        assert svc.get_notebook("nonexistent") is None


class TestUpdateNotebook:
    def test_partial_update(self, svc):
        nb = svc.create_notebook("Old")
        updated = svc.update_notebook(nb["id"], name="New")
        assert updated["name"] == "New"
        assert updated["color"] == "#3B82F6"  # unchanged

    def test_update_not_found(self, svc):
        assert svc.update_notebook("nope", name="X") is None


class TestDeleteNotebook:
    def test_cascades_records(self, svc):
        nb = svc.create_notebook("NB")
        svc.add_record(nb["id"], "blog", "T")
        assert svc.delete_notebook(nb["id"]) is True
        assert svc.get_notebook(nb["id"]) is None

    def test_delete_not_found(self, svc):
        assert svc.delete_notebook("nope") is False


class TestRecords:
    def test_add_record(self, svc):
        nb = svc.create_notebook("NB")
        rec = svc.add_record(nb["id"], "blog", "Title", content="body")
        assert rec is not None
        assert rec["record_type"] == "blog"
        assert rec["title"] == "Title"

    def test_add_record_with_source_id(self, svc):
        nb = svc.create_notebook("NB")
        rec = svc.add_record(nb["id"], "research", "T", source_id="hist-001")
        assert rec["source_id"] == "hist-001"

    def test_add_record_to_nonexistent_notebook(self, svc):
        assert svc.add_record("nope", "blog", "T") is None

    def test_remove_record_success(self, svc):
        nb = svc.create_notebook("NB")
        rec = svc.add_record(nb["id"], "blog", "T")
        assert svc.remove_record(nb["id"], rec["id"]) is True

    def test_remove_record_not_found(self, svc):
        nb = svc.create_notebook("NB")
        assert svc.remove_record(nb["id"], "nope") is False


class TestStatistics:
    def test_empty(self, svc):
        stats = svc.get_statistics()
        assert stats["notebook_count"] == 0
        assert stats["record_count"] == 0
        assert stats["by_type"] == {}

    def test_with_data(self, svc):
        nb = svc.create_notebook("NB")
        svc.add_record(nb["id"], "blog", "T1")
        svc.add_record(nb["id"], "blog", "T2")
        svc.add_record(nb["id"], "note", "T3")
        stats = svc.get_statistics()
        assert stats["notebook_count"] == 1
        assert stats["record_count"] == 3
        assert stats["by_type"]["blog"] == 2
        assert stats["by_type"]["note"] == 1


class TestScenarios:
    def test_full_lifecycle(self, svc):
        nb = svc.create_notebook("Life")
        rec = svc.add_record(nb["id"], "blog", "Post")
        detail = svc.get_notebook(nb["id"])
        assert len(detail["records"]) == 1
        svc.remove_record(nb["id"], rec["id"])
        detail = svc.get_notebook(nb["id"])
        assert len(detail["records"]) == 0
        svc.delete_notebook(nb["id"])
        assert svc.get_notebook(nb["id"]) is None

    def test_multiple_notebooks_isolation(self, svc):
        nb1 = svc.create_notebook("NB1")
        nb2 = svc.create_notebook("NB2")
        svc.add_record(nb1["id"], "blog", "T1")
        svc.add_record(nb2["id"], "note", "T2")
        d1 = svc.get_notebook(nb1["id"])
        d2 = svc.get_notebook(nb2["id"])
        assert len(d1["records"]) == 1
        assert d1["records"][0]["record_type"] == "blog"
        assert len(d2["records"]) == 1
        assert d2["records"][0]["record_type"] == "note"
