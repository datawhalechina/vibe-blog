"""
vibe-reviewer 数据库模型

新增表，不修改现有表
"""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据库路径
_db_path: Optional[str] = None


def init_reviewer_tables(db_path: str = None):
    """
    初始化 vibe-reviewer 相关表
    
    Args:
        db_path: 数据库文件路径，默认使用 vibe-blog 的数据库
    """
    global _db_path
    
    if db_path is None:
        base_dir = Path(__file__).parent.parent.parent
        db_path = str(base_dir / "data" / "vibe_reviewer.db")
    
    _db_path = db_path
    
    # 确保目录存在
    try:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError):
        logger.warning(f"无法创建数据库目录，使用内存数据库")
        _db_path = ":memory:"
    
    # 创建表
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        
        # 数据库迁移：添加新列（如果不存在）
        try:
            # 检查 original_text 列是否存在
            cursor = conn.execute("PRAGMA table_info(reviewer_issues)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'original_text' not in columns:
                conn.execute("ALTER TABLE reviewer_issues ADD COLUMN original_text TEXT")
                logger.info("数据库迁移：添加 original_text 列")
        except Exception as e:
            logger.debug(f"数据库迁移检查: {e}")
    
    logger.info(f"vibe-reviewer 数据库已初始化: {_db_path}")


@contextmanager
def get_connection():
    """获取数据库连接"""
    if _db_path is None:
        raise RuntimeError("数据库未初始化，请先调用 init_reviewer_tables()")
    
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ========== 数据库 Schema ==========

SCHEMA_SQL = '''
-- tutorials (教程表)
CREATE TABLE IF NOT EXISTS reviewer_tutorials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    git_url         TEXT NOT NULL UNIQUE,
    local_path      TEXT,
    description     TEXT,
    branch          TEXT DEFAULT 'main',
    
    -- 配置
    enable_search   BOOLEAN DEFAULT TRUE,
    max_search_rounds INTEGER DEFAULT 2,
    
    -- 统计信息
    total_chapters  INTEGER DEFAULT 0,
    total_issues    INTEGER DEFAULT 0,
    high_issues     INTEGER DEFAULT 0,
    medium_issues   INTEGER DEFAULT 0,
    low_issues      INTEGER DEFAULT 0,
    resolved_issues INTEGER DEFAULT 0,
    
    -- 评分
    avg_depth_score       REAL DEFAULT 0,
    avg_quality_score     REAL DEFAULT 0,
    avg_readability_score REAL DEFAULT 0,
    overall_score         REAL DEFAULT 0,
    
    -- 可读性分布
    readability_distribution TEXT,
    
    -- 状态
    status          TEXT DEFAULT 'pending',
    error_message   TEXT,
    last_evaluated  TIMESTAMP,
    evaluation_duration INTEGER,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviewer_tutorials_status ON reviewer_tutorials(status);
CREATE INDEX IF NOT EXISTS idx_reviewer_tutorials_overall_score ON reviewer_tutorials(overall_score);

-- chapters (章节表)
CREATE TABLE IF NOT EXISTS reviewer_chapters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tutorial_id     INTEGER NOT NULL,
    
    -- 文件信息
    file_path       TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    title           TEXT,
    chapter_order   INTEGER DEFAULT 0,
    word_count      INTEGER DEFAULT 0,
    content_hash    TEXT,
    
    -- 原文存储
    raw_content     TEXT,
    
    -- 图片信息
    image_count     INTEGER DEFAULT 0,
    
    -- 内容摘要
    content_type    TEXT,
    summary_topic       TEXT,
    summary_core_points TEXT,
    summary_key_terms   TEXT,
    summary_fact_claims TEXT,
    
    -- 评分
    depth_score         INTEGER DEFAULT 0,
    quality_score       INTEGER DEFAULT 0,
    readability_score   INTEGER DEFAULT 0,
    readability_level   TEXT,
    overall_score       INTEGER DEFAULT 0,
    
    -- 子维度得分
    logic_score         INTEGER DEFAULT 0,
    accuracy_score      INTEGER DEFAULT 0,
    completeness_score  INTEGER DEFAULT 0,
    vocabulary_score    INTEGER DEFAULT 0,
    syntax_score        INTEGER DEFAULT 0,
    discourse_score     INTEGER DEFAULT 0,
    surface_score       INTEGER DEFAULT 0,
    
    -- 问题统计
    total_issues    INTEGER DEFAULT 0,
    high_issues     INTEGER DEFAULT 0,
    medium_issues   INTEGER DEFAULT 0,
    low_issues      INTEGER DEFAULT 0,
    
    -- 状态
    status          TEXT DEFAULT 'pending',
    error_message   TEXT,
    evaluated_at    TIMESTAMP,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tutorial_id) REFERENCES reviewer_tutorials(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviewer_chapters_tutorial_id ON reviewer_chapters(tutorial_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_chapters_status ON reviewer_chapters(status);

-- issues (问题表)
CREATE TABLE IF NOT EXISTS reviewer_issues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id      INTEGER NOT NULL,
    tutorial_id     INTEGER NOT NULL,
    
    -- 问题信息
    category        TEXT NOT NULL,
    issue_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    location        TEXT,
    description     TEXT NOT NULL,
    suggestion      TEXT,
    reference       TEXT,
    original_text   TEXT,
    
    -- 优先级
    priority        INTEGER DEFAULT 5,
    estimated_effort TEXT DEFAULT 'medium',
    
    -- 状态
    is_resolved     BOOLEAN DEFAULT FALSE,
    resolved_at     TIMESTAMP,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (chapter_id) REFERENCES reviewer_chapters(id) ON DELETE CASCADE,
    FOREIGN KEY (tutorial_id) REFERENCES reviewer_tutorials(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviewer_issues_chapter_id ON reviewer_issues(chapter_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_issues_tutorial_id ON reviewer_issues(tutorial_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_issues_severity ON reviewer_issues(severity);

-- images (图片表)
CREATE TABLE IF NOT EXISTS reviewer_images (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id      INTEGER NOT NULL,
    tutorial_id     INTEGER NOT NULL,
    
    -- 图片信息
    image_path      TEXT NOT NULL,
    image_url       TEXT,
    alt_text        TEXT,
    position        INTEGER DEFAULT 0,
    
    -- 多模态理解结果
    description     TEXT,
    detected_text   TEXT,
    image_type      TEXT,
    relevance_score REAL,
    quality_score   INTEGER DEFAULT 0,
    
    -- 审核结果
    issues          TEXT,
    suggestions     TEXT,
    
    -- 状态
    status          TEXT DEFAULT 'pending',
    error_message   TEXT,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (chapter_id) REFERENCES reviewer_chapters(id) ON DELETE CASCADE,
    FOREIGN KEY (tutorial_id) REFERENCES reviewer_tutorials(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviewer_images_chapter_id ON reviewer_images(chapter_id);

-- search_references (搜索参考资料表)
CREATE TABLE IF NOT EXISTS reviewer_search_references (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id      INTEGER NOT NULL,
    
    -- 搜索信息
    search_round    INTEGER NOT NULL,
    search_query    TEXT NOT NULL,
    search_purpose  TEXT,
    
    -- 结果信息
    source_url      TEXT,
    source_title    TEXT,
    source_domain   TEXT,
    snippet         TEXT,
    full_content    TEXT,
    
    -- 评估
    relevance_score REAL,
    credibility     TEXT,
    
    -- 使用情况
    used_for_verification BOOLEAN DEFAULT FALSE,
    related_issue_ids TEXT,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (chapter_id) REFERENCES reviewer_chapters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviewer_search_references_chapter_id ON reviewer_search_references(chapter_id);

-- evaluation_history (评估历史表)
CREATE TABLE IF NOT EXISTS reviewer_evaluation_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tutorial_id     INTEGER NOT NULL,
    
    -- 快照信息
    total_chapters  INTEGER,
    total_issues    INTEGER,
    high_issues     INTEGER,
    medium_issues   INTEGER,
    low_issues      INTEGER,
    resolved_issues INTEGER,
    overall_score   REAL,
    
    -- 各维度平均分
    avg_depth_score       REAL,
    avg_quality_score     REAL,
    avg_readability_score REAL,
    
    -- 可读性分布
    readability_distribution TEXT,
    
    -- 详细结果
    result_summary  TEXT,
    chapters_snapshot TEXT,
    
    -- 对比信息
    score_change    REAL,
    issues_change   INTEGER,
    
    -- 元信息
    evaluation_duration INTEGER,
    evaluated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tutorial_id) REFERENCES reviewer_tutorials(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviewer_evaluation_history_tutorial_id ON reviewer_evaluation_history(tutorial_id);

-- 视图: 教程概览
CREATE VIEW IF NOT EXISTS v_reviewer_tutorial_overview AS
SELECT 
    t.*,
    (SELECT COUNT(*) FROM reviewer_chapters c WHERE c.tutorial_id = t.id) as chapter_count,
    (SELECT COUNT(*) FROM reviewer_issues i WHERE i.tutorial_id = t.id AND i.is_resolved = FALSE) as unresolved_issues
FROM reviewer_tutorials t;

-- 视图: 章节详情
CREATE VIEW IF NOT EXISTS v_reviewer_chapter_details AS
SELECT 
    c.*,
    t.name as tutorial_name,
    t.git_url as tutorial_git_url,
    (SELECT COUNT(*) FROM reviewer_issues i WHERE i.chapter_id = c.id) as issue_count,
    (SELECT COUNT(*) FROM reviewer_images img WHERE img.chapter_id = c.id) as image_count_actual
FROM reviewer_chapters c
JOIN reviewer_tutorials t ON c.tutorial_id = t.id;
'''


# ========== 模型类 ==========

class TutorialModel:
    """教程模型"""
    
    @staticmethod
    def create(name: str, git_url: str, branch: str = "main", 
               enable_search: bool = True, max_search_rounds: int = 2) -> int:
        """创建教程"""
        with get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO reviewer_tutorials (name, git_url, branch, enable_search, max_search_rounds)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, git_url, branch, enable_search, max_search_rounds))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(tutorial_id: int) -> Optional[Dict]:
        """根据 ID 获取教程"""
        with get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM reviewer_tutorials WHERE id = ?', 
                (tutorial_id,)
            ).fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_git_url(git_url: str) -> Optional[Dict]:
        """根据 Git URL 获取教程"""
        with get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM reviewer_tutorials WHERE git_url = ?', 
                (git_url,)
            ).fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_all() -> List[Dict]:
        """获取所有教程"""
        with get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM reviewer_tutorials ORDER BY created_at DESC'
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def update_status(tutorial_id: int, status: str, error_message: str = None):
        """更新教程状态"""
        with get_connection() as conn:
            conn.execute('''
                UPDATE reviewer_tutorials 
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, error_message, tutorial_id))
    
    @staticmethod
    def update_scores(tutorial_id: int, overall_score: float, 
                      avg_depth: float, avg_quality: float, avg_readability: float,
                      total_chapters: int, total_issues: int,
                      high_issues: int, medium_issues: int, low_issues: int):
        """更新教程评分"""
        with get_connection() as conn:
            conn.execute('''
                UPDATE reviewer_tutorials 
                SET overall_score = ?, avg_depth_score = ?, avg_quality_score = ?, 
                    avg_readability_score = ?, total_chapters = ?, total_issues = ?,
                    high_issues = ?, medium_issues = ?, low_issues = ?,
                    last_evaluated = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (overall_score, avg_depth, avg_quality, avg_readability,
                  total_chapters, total_issues, high_issues, medium_issues, low_issues,
                  tutorial_id))
    
    @staticmethod
    def delete(tutorial_id: int):
        """删除教程"""
        with get_connection() as conn:
            conn.execute('DELETE FROM reviewer_tutorials WHERE id = ?', (tutorial_id,))


class ChapterModel:
    """章节模型"""
    
    @staticmethod
    def create(tutorial_id: int, file_path: str, file_name: str, 
               title: str = None, chapter_order: int = 0,
               raw_content: str = None, content_hash: str = None) -> int:
        """创建或更新章节（按 tutorial_id + file_path 去重）"""
        word_count = len(raw_content) if raw_content else 0
        with get_connection() as conn:
            # 先检查是否已存在
            existing = conn.execute(
                'SELECT id FROM reviewer_chapters WHERE tutorial_id = ? AND file_path = ?',
                (tutorial_id, file_path)
            ).fetchone()
            
            if existing:
                # 更新已存在的章节
                conn.execute('''
                    UPDATE reviewer_chapters 
                    SET file_name = ?, title = ?, chapter_order = ?, raw_content = ?, 
                        content_hash = ?, word_count = ?, status = 'pending',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (file_name, title, chapter_order, raw_content, content_hash, word_count, existing['id']))
                return existing['id']
            else:
                # 创建新章节
                cursor = conn.execute('''
                    INSERT INTO reviewer_chapters 
                    (tutorial_id, file_path, file_name, title, chapter_order, raw_content, content_hash, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (tutorial_id, file_path, file_name, title, chapter_order, raw_content, content_hash, word_count))
                return cursor.lastrowid
    
    @staticmethod
    def get_by_id(chapter_id: int) -> Optional[Dict]:
        """根据 ID 获取章节"""
        with get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM reviewer_chapters WHERE id = ?', 
                (chapter_id,)
            ).fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_tutorial(tutorial_id: int) -> List[Dict]:
        """获取教程的所有章节"""
        with get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM reviewer_chapters WHERE tutorial_id = ? ORDER BY chapter_order',
                (tutorial_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def update_scores(chapter_id: int, overall_score: int,
                      depth_score: int, quality_score: int, readability_score: int,
                      readability_level: str, total_issues: int,
                      high_issues: int, medium_issues: int, low_issues: int):
        """更新章节评分"""
        with get_connection() as conn:
            conn.execute('''
                UPDATE reviewer_chapters 
                SET overall_score = ?, depth_score = ?, quality_score = ?, 
                    readability_score = ?, readability_level = ?,
                    total_issues = ?, high_issues = ?, medium_issues = ?, low_issues = ?,
                    status = 'completed', evaluated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (overall_score, depth_score, quality_score, readability_score,
                  readability_level, total_issues, high_issues, medium_issues, low_issues,
                  chapter_id))
    
    @staticmethod
    def get_by_hash(tutorial_id: int, content_hash: str) -> Optional[Dict]:
        """根据内容哈希获取章节 (用于增量更新检测)"""
        with get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM reviewer_chapters WHERE tutorial_id = ? AND content_hash = ?',
                (tutorial_id, content_hash)
            ).fetchone()
            return dict(row) if row else None


class IssueModel:
    """问题模型"""
    
    @staticmethod
    def create(chapter_id: int, tutorial_id: int, category: str, issue_type: str,
               severity: str, location: str, description: str, 
               suggestion: str = None, reference: str = None,
               original_text: str = None,
               priority: int = 5, estimated_effort: str = "medium") -> int:
        """创建问题"""
        with get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO reviewer_issues 
                (chapter_id, tutorial_id, category, issue_type, severity, location, 
                 description, suggestion, reference, original_text, priority, estimated_effort)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (chapter_id, tutorial_id, category, issue_type, severity, location,
                  description, suggestion, reference, original_text, priority, estimated_effort))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_chapter(chapter_id: int) -> List[Dict]:
        """获取章节的所有问题"""
        with get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM reviewer_issues WHERE chapter_id = ? ORDER BY priority, severity DESC',
                (chapter_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_tutorial(tutorial_id: int, severity: str = None) -> List[Dict]:
        """获取教程的所有问题"""
        with get_connection() as conn:
            if severity:
                rows = conn.execute(
                    'SELECT * FROM reviewer_issues WHERE tutorial_id = ? AND severity = ? ORDER BY priority',
                    (tutorial_id, severity)
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM reviewer_issues WHERE tutorial_id = ? ORDER BY priority, severity DESC',
                    (tutorial_id,)
                ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def mark_resolved(issue_id: int, resolved: bool = True):
        """标记问题已解决"""
        with get_connection() as conn:
            conn.execute('''
                UPDATE reviewer_issues 
                SET is_resolved = ?, resolved_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE id = ?
            ''', (resolved, resolved, issue_id))
    
    @staticmethod
    def delete_by_chapter(chapter_id: int):
        """删除章节的所有问题"""
        with get_connection() as conn:
            conn.execute('DELETE FROM reviewer_issues WHERE chapter_id = ?', (chapter_id,))


class ImageModel:
    """图片模型"""
    
    @staticmethod
    def create(chapter_id: int, tutorial_id: int, image_path: str,
               alt_text: str = None, position: int = 0) -> int:
        """创建图片记录"""
        with get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO reviewer_images 
                (chapter_id, tutorial_id, image_path, alt_text, position)
                VALUES (?, ?, ?, ?, ?)
            ''', (chapter_id, tutorial_id, image_path, alt_text, position))
            return cursor.lastrowid
    
    @staticmethod
    def update_analysis(image_id: int, description: str, detected_text: str,
                        image_type: str, relevance_score: float, quality_score: int):
        """更新图片分析结果"""
        with get_connection() as conn:
            conn.execute('''
                UPDATE reviewer_images 
                SET description = ?, detected_text = ?, image_type = ?,
                    relevance_score = ?, quality_score = ?, status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (description, detected_text, image_type, relevance_score, quality_score, image_id))
    
    @staticmethod
    def get_by_chapter(chapter_id: int) -> List[Dict]:
        """获取章节的所有图片"""
        with get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM reviewer_images WHERE chapter_id = ? ORDER BY position',
                (chapter_id,)
            ).fetchall()
            return [dict(row) for row in rows]
