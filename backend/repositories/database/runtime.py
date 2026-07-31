"""SQLite connection lifecycle, schema creation, and migrations."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("services.database_service")


class SQLiteRuntime:
    """Own the shared SQLite lifecycle used by application repositories."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典形式的结果
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize(self, connection_provider=None, migration_callback=None):
        """初始化数据库表"""
        connections = connection_provider or self
        with connections.get_connection() as conn:
            conn.executescript('''
                -- 文档表：存储上传的文档元数据
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    markdown_content TEXT,
                    markdown_length INTEGER DEFAULT 0,
                    summary TEXT,
                    mineru_folder TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parsed_at TIMESTAMP
                );

                -- 知识分块表：存储文档的分块内容（二期新增）
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_type TEXT DEFAULT 'text',
                    title TEXT,
                    content TEXT NOT NULL,
                    start_pos INTEGER,
                    end_pos INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                -- 文档图片表：存储 PDF 中提取的图片及摘要（二期新增）
                CREATE TABLE IF NOT EXISTS document_images (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    image_index INTEGER NOT NULL,
                    image_path TEXT NOT NULL,
                    caption TEXT,
                    page_num INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                -- 历史记录表：存储问答历史快照
                CREATE TABLE IF NOT EXISTS history_records (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    article_type TEXT DEFAULT 'tutorial',
                    target_length TEXT DEFAULT 'medium',
                    markdown_content TEXT,
                    outline TEXT,
                    sections_count INTEGER DEFAULT 0,
                    code_blocks_count INTEGER DEFAULT 0,
                    images_count INTEGER DEFAULT 0,
                    review_score INTEGER DEFAULT 0,
                    cover_image TEXT,
                    cover_video TEXT,
                    target_sections_count INTEGER,
                    target_images_count INTEGER,
                    target_code_blocks_count INTEGER,
                    target_word_count INTEGER,
                    citations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- 书籍表：存储聚合的教程书籍
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    theme TEXT DEFAULT 'general',
                    cover_image TEXT,
                    outline TEXT,
                    chapters_count INTEGER DEFAULT 0,
                    total_word_count INTEGER DEFAULT 0,
                    blogs_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- 书籍章节表：存储书籍的章节结构
                CREATE TABLE IF NOT EXISTS book_chapters (
                    id TEXT PRIMARY KEY,
                    book_id TEXT NOT NULL,
                    chapter_index INTEGER NOT NULL,
                    chapter_title TEXT NOT NULL,
                    section_index TEXT,
                    section_title TEXT,
                    blog_id TEXT,
                    has_content INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
                    FOREIGN KEY (blog_id) REFERENCES history_records(id) ON DELETE SET NULL
                );

                -- 创建索引
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
                CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON knowledge_chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_type ON knowledge_chunks(chunk_type);
                CREATE INDEX IF NOT EXISTS idx_images_document_id ON document_images(document_id);
                CREATE INDEX IF NOT EXISTS idx_history_created_at ON history_records(created_at);
                CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);
                CREATE INDEX IF NOT EXISTS idx_books_theme ON books(theme);
                CREATE INDEX IF NOT EXISTS idx_book_chapters_book_id ON book_chapters(book_id);
                CREATE INDEX IF NOT EXISTS idx_book_chapters_blog_id ON book_chapters(blog_id);
            ''')
        logger.info("数据库表初始化完成")

        # 执行数据库迁移
        if migration_callback is None:
            self.migrate(connection_provider=connections)
        else:
            migration_callback()

    def migrate(self, connection_provider=None):
        """数据库迁移：检查并添加新字段"""
        connections = connection_provider or self
        with connections.get_connection() as conn:
            # 迁移 history_records 表
            cursor = conn.execute("PRAGMA table_info(history_records)")
            columns = [row[1] for row in cursor.fetchall()]

            new_columns = {
                'target_sections_count': 'INTEGER',
                'target_images_count': 'INTEGER',
                'target_code_blocks_count': 'INTEGER',
                'target_word_count': 'INTEGER',
                'book_id': 'TEXT',
                'summary': 'TEXT',  # 博客摘要
                'citations': 'TEXT',  # 引用来源（JSON）
            }

            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    logger.info(f"迁移数据库：添加 history_records.{col_name} 列")
                    conn.execute(f"ALTER TABLE history_records ADD COLUMN {col_name} {col_type}")

            # 迁移 books 表 - 添加首页相关字段
            cursor = conn.execute("PRAGMA table_info(books)")
            book_columns = [row[1] for row in cursor.fetchall()]

            book_new_columns = {
                'homepage_content': 'TEXT',   # 首页完整内容（JSON 格式）
                'full_outline': 'TEXT',       # 完整大纲（包含待建设章节）
                'highlights': 'TEXT',         # 项目亮点（JSON 格式）
                'target_audience': 'TEXT',    # 目标受众（JSON 格式）
                'prerequisites': 'TEXT'       # 前置要求（JSON 格式）
            }

            for col_name, col_type in book_new_columns.items():
                if col_name not in book_columns:
                    logger.info(f"迁移数据库：添加 books.{col_name} 列")
                    conn.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_type}")

            # 迁移后创建依赖新字段的索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_book_id ON history_records(book_id)')

            # ========== 小红书支持迁移 ==========
            xhs_columns = {
                # 内容类型区分
                'content_type': "TEXT DEFAULT 'blog'",      # 'blog' | 'xhs'

                # 记录关联
                'source_id': 'TEXT',                        # 来源记录ID（小红书来源于哪个博客）
                'derived_ids': 'TEXT',                      # 衍生记录ID（JSON数组，博客衍生了哪些小红书）

                # 小红书专属字段
                'xhs_style': 'TEXT',                        # hand_drawn | claymation
                'xhs_layout_type': 'TEXT',                  # 布局类型
                'xhs_image_urls': 'TEXT',                   # 图片URL列表（JSON）
                'xhs_copy_text': 'TEXT',                    # 小红书文案
                'xhs_hashtags': 'TEXT',                     # 话题标签（JSON）
                'xhs_publish_url': 'TEXT',                  # 小红书发布链接

                # 多平台发布状态
                'publish_platforms': 'TEXT'                 # JSON格式
            }

            for col_name, col_type in xhs_columns.items():
                if col_name not in columns:
                    logger.info(f"迁移数据库：添加 history_records.{col_name} 列")
                    conn.execute(f"ALTER TABLE history_records ADD COLUMN {col_name} {col_type}")

            # 创建小红书相关索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_content_type ON history_records(content_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_source_id ON history_records(source_id)')
