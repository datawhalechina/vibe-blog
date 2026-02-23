"""
1003.09 笔记本管理服务

迁移自 DeepTutor NotebookManager，适配 vibe-blog SQLite 存储。
提供笔记本 CRUD + 记录管理 + 统计。
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NotebookService:
    """笔记本管理服务"""

    def __init__(self, db_path: str = ""):
        self._db_path = db_path
        self._conn = None
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._db_path:
                self._conn = sqlite3.connect(self._db_path)
            else:
                self._conn = sqlite3.connect(":memory:")
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def _init_tables(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notebooks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#3B82F6',
                icon TEXT DEFAULT 'book',
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS notebook_records (
                id TEXT PRIMARY KEY,
                notebook_id TEXT NOT NULL,
                record_type TEXT NOT NULL,
                title TEXT NOT NULL,
                user_query TEXT DEFAULT '',
                content TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                source_id TEXT,
                kb_name TEXT,
                created_at TEXT,
                FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_notebook_records_notebook_id
                ON notebook_records(notebook_id);
            CREATE INDEX IF NOT EXISTS idx_notebook_records_type
                ON notebook_records(record_type);
            CREATE INDEX IF NOT EXISTS idx_notebook_records_source_id
                ON notebook_records(source_id);
        """)
        conn.commit()

    # ── Notebook CRUD ──

    def create_notebook(
        self, name: str, description: str = "",
        color: str = "#3B82F6", icon: str = "book",
    ) -> dict:
        now = datetime.utcnow().isoformat()
        nb_id = uuid.uuid4().hex[:8]
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO notebooks (id, name, description, color, icon, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nb_id, name, description, color, icon, now, now),
        )
        conn.commit()
        return {"id": nb_id, "name": name, "description": description,
                "color": color, "icon": icon, "created_at": now, "updated_at": now}

    def list_notebooks(self) -> List[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT n.*, COUNT(r.id) AS record_count "
            "FROM notebooks n LEFT JOIN notebook_records r ON n.id = r.notebook_id "
            "GROUP BY n.id ORDER BY n.updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_notebook(self, notebook_id: str) -> Optional[dict]:
        conn = self._get_conn()
        nb = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
        if nb is None:
            return None
        result = dict(nb)
        records = conn.execute(
            "SELECT * FROM notebook_records WHERE notebook_id = ? ORDER BY created_at DESC",
            (notebook_id,),
        ).fetchall()
        result["records"] = [dict(r) for r in records]
        return result

    def update_notebook(self, notebook_id: str, **kwargs) -> Optional[dict]:
        conn = self._get_conn()
        nb = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
        if nb is None:
            return None
        allowed = {"name", "description", "color", "icon"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return dict(nb)
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE notebooks SET {set_clause} WHERE id = ?",
            (*updates.values(), notebook_id),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone())

    def delete_notebook(self, notebook_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
        conn.commit()
        return cur.rowcount > 0

    # ── Record 管理 ──

    def add_record(
        self, notebook_id: str, record_type: str, title: str,
        user_query: str = "", content: str = "",
        metadata: Optional[Dict] = None, source_id: Optional[str] = None,
        kb_name: Optional[str] = None,
    ) -> Optional[dict]:
        conn = self._get_conn()
        nb = conn.execute("SELECT id FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
        if nb is None:
            return None
        now = datetime.utcnow().isoformat()
        rec_id = uuid.uuid4().hex[:8]
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        conn.execute(
            "INSERT INTO notebook_records "
            "(id, notebook_id, record_type, title, user_query, content, metadata, source_id, kb_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rec_id, notebook_id, record_type, title, user_query, content, meta_str, source_id, kb_name, now),
        )
        conn.execute("UPDATE notebooks SET updated_at = ? WHERE id = ?", (now, notebook_id))
        conn.commit()
        return {"id": rec_id, "notebook_id": notebook_id, "record_type": record_type,
                "title": title, "user_query": user_query, "content": content,
                "metadata": metadata or {}, "source_id": source_id, "kb_name": kb_name,
                "created_at": now}

    def remove_record(self, notebook_id: str, record_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM notebook_records WHERE id = ? AND notebook_id = ?",
            (record_id, notebook_id),
        )
        if cur.rowcount > 0:
            conn.execute(
                "UPDATE notebooks SET updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), notebook_id),
            )
            conn.commit()
            return True
        conn.commit()
        return False

    # ── 统计 ──

    def get_statistics(self) -> dict:
        conn = self._get_conn()
        nb_count = conn.execute("SELECT COUNT(*) FROM notebooks").fetchone()[0]
        rec_count = conn.execute("SELECT COUNT(*) FROM notebook_records").fetchone()[0]
        type_rows = conn.execute(
            "SELECT record_type, COUNT(*) AS cnt FROM notebook_records GROUP BY record_type"
        ).fetchall()
        by_type = {r["record_type"]: r["cnt"] for r in type_rows}
        return {"notebook_count": nb_count, "record_count": rec_count, "by_type": by_type}
