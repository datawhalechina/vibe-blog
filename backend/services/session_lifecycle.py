"""
会话生命周期管理

提供通用会话 CRUD + 状态机 + TTL 过期 + 容量限制。
SQLite 持久化存储。
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SessionType(str, Enum):
    BLOG_GENERATE = "blog_generate"
    CHAT_WRITING = "chat_writing"
    XHS = "xhs"
    PODCAST = "podcast"


@dataclass
class Session:
    session_id: str
    session_type: SessionType
    title: str
    status: SessionStatus = SessionStatus.CREATED
    task_id: Optional[str] = None
    thread_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    expires_at: Optional[str] = None


class SessionLifecycleManager:
    """通用会话生命周期管理器 -- SQLite 持久化"""

    MAX_SESSIONS = 200

    def __init__(self, db_path: str = ""):
        if db_path:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        else:
            self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'created',
                task_id TEXT,
                thread_id TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_type_status "
            "ON sessions(session_type, status)"
        )
        self._conn.commit()

    def create(self, session_type: SessionType, title: str,
               task_id: str = None, ttl_hours: int = 72,
               **meta) -> Session:
        now = datetime.now(timezone.utc).isoformat()
        expires = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
        session = Session(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            session_type=session_type,
            title=title[:120],
            task_id=task_id,
            thread_id=f"blog_{uuid.uuid4().hex[:8]}",
            metadata=meta,
            created_at=now,
            updated_at=now,
            expires_at=expires,
        )
        cols = asdict(session)
        cols["metadata"] = json.dumps(cols["metadata"], ensure_ascii=False)
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols.keys())
        self._conn.execute(
            f"INSERT INTO sessions ({col_names}) VALUES ({placeholders})",
            list(cols.values()),
        )
        self._conn.commit()
        self._enforce_capacity()
        return session

    def get(self, session_id: str) -> Optional[Session]:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def list_sessions(self, session_type: SessionType = None,
                      status: SessionStatus = None,
                      limit: int = 50) -> List[Session]:
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        if session_type:
            query += " AND session_type = ?"
            params.append(session_type.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_session(r) for r in rows]

    def update_status(self, session_id: str, status: SessionStatus) -> Optional[Session]:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
            (status.value, now, session_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return None
        return self.get(session_id)

    def delete(self, session_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM sessions WHERE session_id = ?", (session_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        self._conn.commit()
        return cur.rowcount

    def _enforce_capacity(self):
        count = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        if count > self.MAX_SESSIONS:
            excess = count - self.MAX_SESSIONS
            self._conn.execute(
                "DELETE FROM sessions WHERE session_id IN "
                "(SELECT session_id FROM sessions ORDER BY updated_at ASC LIMIT ?)",
                (excess,),
            )
            self._conn.commit()

    def _row_to_session(self, row) -> Session:
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata", "{}"))
        d["session_type"] = SessionType(d["session_type"])
        d["status"] = SessionStatus(d["status"])
        return Session(**d)
