"""
WritingSession 数据模型 + WritingSessionManager SQLite 持久化
对话式写作会话管理
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List
import sqlite3


@dataclass
class WritingSession:
    session_id: str
    topic: str
    user_id: str = ""
    article_type: str = "problem-solution"
    target_audience: str = "beginner"
    target_length: str = "medium"
    outline: Optional[dict] = None
    sections: List[dict] = field(default_factory=list)
    search_results: List[dict] = field(default_factory=list)
    research_summary: Optional[str] = None
    key_concepts: List[str] = field(default_factory=list)
    code_blocks: List[dict] = field(default_factory=list)
    images: List[dict] = field(default_factory=list)
    status: str = "created"
    created_at: str = ""
    updated_at: str = ""


# JSON 序列化的字段列表
_JSON_FIELDS = {"outline", "sections", "search_results", "key_concepts", "code_blocks", "images"}

# 所有可更新的字段
_ALL_FIELDS = {
    "topic", "user_id", "article_type", "target_audience", "target_length",
    "outline", "sections", "search_results", "research_summary",
    "key_concepts", "code_blocks", "images", "status",
}


class WritingSessionManager:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS writing_sessions (
                session_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                user_id TEXT DEFAULT '',
                article_type TEXT DEFAULT 'problem-solution',
                target_audience TEXT DEFAULT 'beginner',
                target_length TEXT DEFAULT 'medium',
                outline TEXT,
                sections TEXT,
                search_results TEXT,
                research_summary TEXT,
                key_concepts TEXT,
                code_blocks TEXT,
                images TEXT,
                status TEXT DEFAULT 'created',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.commit()
        self._migrate()

    def _migrate(self):
        cursor = self._conn.execute("PRAGMA table_info(writing_sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        if "user_id" not in columns:
            self._conn.execute("ALTER TABLE writing_sessions ADD COLUMN user_id TEXT DEFAULT ''")
            self._conn.commit()

    def _row_to_session(self, row: sqlite3.Row) -> WritingSession:
        d = dict(row)
        for f in _JSON_FIELDS:
            if d.get(f) is not None:
                d[f] = json.loads(d[f])
            elif f in ("sections", "search_results", "key_concepts", "code_blocks", "images"):
                d[f] = []
        return WritingSession(**d)

    def create(self, topic: str, user_id: str = "", **kwargs) -> WritingSession:
        now = datetime.now(timezone.utc).isoformat()
        session = WritingSession(
            session_id=f"ws_{uuid.uuid4().hex[:12]}",
            topic=topic,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            **{k: v for k, v in kwargs.items() if k in _ALL_FIELDS},
        )
        cols = asdict(session)
        for f in _JSON_FIELDS:
            if cols[f] is not None:
                cols[f] = json.dumps(cols[f], ensure_ascii=False)
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols.keys())
        self._conn.execute(
            f"INSERT INTO writing_sessions ({col_names}) VALUES ({placeholders})",
            list(cols.values()),
        )
        self._conn.commit()
        return session

    def get(self, session_id: str, user_id: str = None) -> Optional[WritingSession]:
        if user_id:
            row = self._conn.execute(
                "SELECT * FROM writing_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM writing_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def update(self, session_id: str, **kwargs) -> Optional[WritingSession]:
        updates = {k: v for k, v in kwargs.items() if k in _ALL_FIELDS}
        if not updates:
            return self.get(session_id)
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_parts = []
        values = []
        for k, v in updates.items():
            set_parts.append(f"{k} = ?")
            values.append(json.dumps(v, ensure_ascii=False) if k in _JSON_FIELDS and v is not None else v)
        values.append(session_id)
        self._conn.execute(
            f"UPDATE writing_sessions SET {', '.join(set_parts)} WHERE session_id = ?",
            values,
        )
        self._conn.commit()
        return self.get(session_id)

    def list(self, limit: int = 20, offset: int = 0, user_id: str = None) -> List[WritingSession]:
        if user_id:
            rows = self._conn.execute(
                "SELECT * FROM writing_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM writing_sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def delete(self, session_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM writing_sessions WHERE session_id = ?", (session_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0
