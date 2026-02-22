"""
文件夹同步管理服务 -- 本地文件夹与素材库的增量同步
"""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.txt', '.markdown', '.docx', '.pptx', '.xlsx'}


class FolderSyncService:
    def __init__(self, base_dir: str = "materials"):
        self.base_dir = Path(base_dir)
        self.meta_path = self.base_dir / "folder_sync_meta.json"
        self._meta: Dict = self._load_meta()

    def _load_meta(self) -> Dict:
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"linked_folders": []}

    def _save_meta(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False, indent=2)

    def link_folder(self, folder_path: str) -> Dict:
        """关联本地文件夹（幂等）"""
        folder = Path(folder_path).expanduser().resolve()
        if not folder.is_dir():
            raise ValueError(f"文件夹不存在: {folder}")
        folder_id = hashlib.md5(
            str(folder).encode(), usedforsecurity=False
        ).hexdigest()[:8]
        for item in self._meta["linked_folders"]:
            if item["id"] == folder_id:
                return item
        files = self._scan_folder(folder)
        info = {
            "id": folder_id,
            "path": str(folder),
            "added_at": datetime.now().isoformat(),
            "file_count": len(files),
            "synced_files": {},
        }
        self._meta["linked_folders"].append(info)
        self._save_meta()
        return info

    def list_folders(self) -> List[Dict]:
        return self._meta.get("linked_folders", [])

    def unlink_folder(self, folder_id: str) -> bool:
        before = len(self._meta["linked_folders"])
        self._meta["linked_folders"] = [
            f for f in self._meta["linked_folders"] if f["id"] != folder_id
        ]
        if len(self._meta["linked_folders"]) < before:
            self._save_meta()
            return True
        return False

    def detect_changes(self, folder_id: str) -> Dict:
        folder_info = self._get_folder(folder_id)
        folder = Path(folder_info["path"])
        synced = folder_info.get("synced_files", {})
        new_files, modified_files = [], []
        for fp in self._scan_folder(folder):
            mtime = datetime.fromtimestamp(fp.stat().st_mtime).isoformat()
            fp_str = str(fp)
            if fp_str not in synced:
                new_files.append(fp_str)
            elif mtime > synced[fp_str]:
                modified_files.append(fp_str)
        return {
            "new_files": sorted(new_files),
            "modified_files": sorted(modified_files),
            "has_changes": bool(new_files or modified_files),
        }

    def mark_synced(self, folder_id: str, file_paths: List[str]):
        folder_info = self._get_folder(folder_id)
        synced = folder_info.setdefault("synced_files", {})
        for fp in file_paths:
            p = Path(fp)
            if p.exists():
                synced[fp] = datetime.fromtimestamp(p.stat().st_mtime).isoformat()
        folder_info["last_sync"] = datetime.now().isoformat()
        self._save_meta()

    def _get_folder(self, folder_id: str) -> Dict:
        for item in self._meta["linked_folders"]:
            if item["id"] == folder_id:
                return item
        raise ValueError(f"未找到关联文件夹: {folder_id}")

    @staticmethod
    def _scan_folder(folder: Path) -> List[Path]:
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(folder.glob(f"**/*{ext}"))
        return sorted(files)
