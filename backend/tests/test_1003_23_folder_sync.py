"""TDD 测试 — 1003.23 知识库文件夹同步管理"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.folder_sync_service import FolderSyncService, SUPPORTED_EXTENSIONS


@pytest.fixture
def svc(tmp_path):
    """Create a FolderSyncService with a temp base_dir."""
    return FolderSyncService(base_dir=str(tmp_path / "materials"))


@pytest.fixture
def sample_folder(tmp_path):
    """Create a temp folder with a .md file inside."""
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "note.md").write_text("# Hello")
    return folder


class TestLinkFolder:
    def test_link_folder_success(self, svc, sample_folder):
        info = svc.link_folder(str(sample_folder))
        assert "id" in info
        assert info["path"] == str(sample_folder)
        assert info["file_count"] == 1
        assert "added_at" in info

    def test_link_folder_idempotent(self, svc, sample_folder):
        info1 = svc.link_folder(str(sample_folder))
        info2 = svc.link_folder(str(sample_folder))
        assert info1["id"] == info2["id"]
        assert len(svc.list_folders()) == 1

    def test_link_folder_not_exists(self, svc):
        with pytest.raises(ValueError, match="文件夹不存在"):
            svc.link_folder("/nonexistent/path/that/does/not/exist")


class TestListFolders:
    def test_list_folders(self, svc, tmp_path):
        f1 = tmp_path / "folder_a"
        f1.mkdir()
        f2 = tmp_path / "folder_b"
        f2.mkdir()
        svc.link_folder(str(f1))
        svc.link_folder(str(f2))
        folders = svc.list_folders()
        assert len(folders) == 2
        ids = {f["id"] for f in folders}
        assert len(ids) == 2


class TestUnlinkFolder:
    def test_unlink_folder(self, svc, sample_folder):
        info = svc.link_folder(str(sample_folder))
        assert svc.unlink_folder(info["id"]) is True
        assert len(svc.list_folders()) == 0

    def test_unlink_nonexistent(self, svc):
        assert svc.unlink_folder("nonexistent") is False


class TestDetectChanges:
    def test_detect_changes_new_files(self, svc, sample_folder):
        info = svc.link_folder(str(sample_folder))
        changes = svc.detect_changes(info["id"])
        assert changes["has_changes"] is True
        assert len(changes["new_files"]) == 1
        assert str(sample_folder / "note.md") in changes["new_files"]

    def test_detect_changes_modified(self, svc, sample_folder):
        info = svc.link_folder(str(sample_folder))
        md_file = sample_folder / "note.md"
        svc.mark_synced(info["id"], [str(md_file)])
        # Advance mtime by 2 seconds to ensure detection
        future = time.time() + 2
        os.utime(str(md_file), (future, future))
        changes = svc.detect_changes(info["id"])
        assert changes["has_changes"] is True
        assert str(md_file) in changes["modified_files"]

    def test_detect_changes_no_changes(self, svc, sample_folder):
        info = svc.link_folder(str(sample_folder))
        md_file = sample_folder / "note.md"
        svc.mark_synced(info["id"], [str(md_file)])
        changes = svc.detect_changes(info["id"])
        assert changes["has_changes"] is False
        assert changes["new_files"] == []
        assert changes["modified_files"] == []


class TestMarkSynced:
    def test_mark_synced_updates_mtime(self, svc, sample_folder):
        info = svc.link_folder(str(sample_folder))
        md_file = str(sample_folder / "note.md")
        svc.mark_synced(info["id"], [md_file])
        folder_info = svc._get_folder(info["id"])
        assert md_file in folder_info["synced_files"]
        assert "last_sync" in folder_info


class TestScanFolder:
    def test_scan_folder_extensions(self, tmp_path):
        folder = tmp_path / "mixed"
        folder.mkdir()
        # Supported
        (folder / "a.pdf").write_text("")
        (folder / "b.md").write_text("")
        (folder / "c.txt").write_text("")
        (folder / "d.markdown").write_text("")
        (folder / "e.docx").write_text("")
        (folder / "f.pptx").write_text("")
        (folder / "g.xlsx").write_text("")
        # Unsupported
        (folder / "h.jpg").write_text("")
        (folder / "i.py").write_text("")
        (folder / "j.exe").write_text("")
        files = FolderSyncService._scan_folder(folder)
        extensions = {f.suffix for f in files}
        assert extensions == SUPPORTED_EXTENSIONS
        assert len(files) == 7


class TestMetaPersistence:
    def test_meta_persistence(self, tmp_path, sample_folder):
        base = str(tmp_path / "materials")
        svc1 = FolderSyncService(base_dir=base)
        info = svc1.link_folder(str(sample_folder))
        # Create a new instance with the same base_dir
        svc2 = FolderSyncService(base_dir=base)
        folders = svc2.list_folders()
        assert len(folders) == 1
        assert folders[0]["id"] == info["id"]
