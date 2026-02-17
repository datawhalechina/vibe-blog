"""
数据库服务 - 管理文档元数据和知识块
使用 SQLite 存储
"""
import sqlite3
import uuid
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """SQLite 数据库服务"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库服务
        
        Args:
            db_path: 数据库文件路径，默认为 backend/data/banana_blog.db
                    在 Vercel 等只读环境中，自动使用内存数据库
        """
        if db_path is None:
            # 默认路径: backend/data/banana_blog.db
            base_dir = Path(__file__).parent.parent
            db_path = str(base_dir / "data" / "banana_blog.db")
        
        self.db_path = db_path
        
        # 尝试创建目录，如果失败则使用内存数据库
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except (OSError, IOError):
            # Vercel 环境是只读的，使用内存数据库
            logger.warning(f"无法创建数据库目录，使用内存数据库")
            self.db_path = ":memory:"
        
        # 初始化表
        self._init_tables()
        logger.info(f"数据库服务已初始化: {self.db_path}")
    
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
    
    def _init_tables(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
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
        self._migrate_tables()
    
    def _migrate_tables(self):
        """数据库迁移：检查并添加新字段"""
        with self.get_connection() as conn:
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
    
    # ========== 文档操作 ==========
    
    def create_document(
        self, 
        doc_id: str, 
        filename: str, 
        file_path: str, 
        file_size: int, 
        file_type: str
    ) -> Dict[str, Any]:
        """
        创建文档记录
        
        Args:
            doc_id: 文档 ID
            filename: 原始文件名
            file_path: 存储路径
            file_size: 文件大小（字节）
            file_type: 文件类型 (pdf/md/txt)
        
        Returns:
            创建的文档记录
        """
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO documents (id, filename, file_path, file_size, file_type, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (doc_id, filename, file_path, file_size, file_type))
        
        logger.info(f"创建文档记录: {doc_id}, {filename}")
        return self.get_document(doc_id)
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文档记录
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            文档记录字典，不存在返回 None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM documents WHERE id = ?', 
                (doc_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def update_document_status(
        self, 
        doc_id: str, 
        status: str, 
        error_message: str = None
    ):
        """
        更新文档状态
        
        Args:
            doc_id: 文档 ID
            status: 新状态 (pending/parsing/ready/error)
            error_message: 错误信息（可选）
        """
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE documents 
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, error_message, doc_id))
        
        logger.info(f"更新文档状态: {doc_id} -> {status}")
    
    def save_parse_result(
        self, 
        doc_id: str, 
        markdown: str, 
        mineru_folder: str = None
    ):
        """
        保存解析结果
        
        Args:
            doc_id: 文档 ID
            markdown: 解析后的 Markdown 内容
            mineru_folder: MinerU 解析结果目录（PDF 专用）
        """
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE documents 
                SET status = 'ready', 
                    markdown_content = ?, 
                    markdown_length = ?,
                    mineru_folder = ?, 
                    parsed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (markdown, len(markdown), mineru_folder, doc_id))
        
        logger.info(f"保存解析结果: {doc_id}, 长度={len(markdown)}")
    
    def get_documents_by_ids(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取文档
        
        Args:
            doc_ids: 文档 ID 列表
        
        Returns:
            文档记录列表
        """
        if not doc_ids:
            return []
        
        placeholders = ','.join(['?' for _ in doc_ids])
        with self.get_connection() as conn:
            cursor = conn.execute(
                f'SELECT * FROM documents WHERE id IN ({placeholders}) AND status = "ready"',
                doc_ids
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档记录
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            是否删除成功
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                'DELETE FROM documents WHERE id = ?',
                (doc_id,)
            )
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"删除文档: {doc_id}")
        return deleted
    
    def list_documents(
        self, 
        status: str = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        列出文档
        
        Args:
            status: 筛选状态（可选）
            limit: 返回数量限制
        
        Returns:
            文档记录列表
        """
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    'SELECT * FROM documents WHERE status = ? ORDER BY created_at DESC LIMIT ?',
                    (status, limit)
                )
            else:
                cursor = conn.execute(
                    'SELECT * FROM documents ORDER BY created_at DESC LIMIT ?',
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_document_summary(self, doc_id: str, summary: str):
        """
        更新文档摘要（二期新增）
        
        Args:
            doc_id: 文档 ID
            summary: 文档摘要
        """
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE documents 
                SET summary = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (summary, doc_id))
        logger.info(f"更新文档摘要: {doc_id}")
    
    # ========== 知识分块操作（二期新增） ==========
    
    def save_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]):
        """
        保存文档的知识分块
        
        Args:
            doc_id: 文档 ID
            chunks: 分块列表，每个分块包含 {chunk_type, title, content, start_pos, end_pos}
        """
        with self.get_connection() as conn:
            # 先删除旧分块
            conn.execute('DELETE FROM knowledge_chunks WHERE document_id = ?', (doc_id,))
            
            # 插入新分块
            for idx, chunk in enumerate(chunks):
                chunk_id = f"chunk_{doc_id}_{idx}"
                conn.execute('''
                    INSERT INTO knowledge_chunks 
                    (id, document_id, chunk_index, chunk_type, title, content, start_pos, end_pos)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_id,
                    doc_id,
                    idx,
                    chunk.get('chunk_type', 'text'),
                    chunk.get('title', ''),
                    chunk.get('content', ''),
                    chunk.get('start_pos', 0),
                    chunk.get('end_pos', 0)
                ))
        
        logger.info(f"保存知识分块: {doc_id}, 共 {len(chunks)} 块")
    
    def get_chunks_by_document(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        获取文档的所有分块
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            分块列表
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index',
                (doc_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_chunks_by_documents(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取多个文档的分块
        
        Args:
            doc_ids: 文档 ID 列表
        
        Returns:
            分块列表
        """
        if not doc_ids:
            return []
        
        placeholders = ','.join(['?' for _ in doc_ids])
        with self.get_connection() as conn:
            cursor = conn.execute(
                f'SELECT * FROM knowledge_chunks WHERE document_id IN ({placeholders}) ORDER BY document_id, chunk_index',
                doc_ids
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 文档图片操作（二期新增） ==========
    
    def save_images(self, doc_id: str, images: List[Dict[str, Any]]):
        """
        保存文档的图片信息
        
        Args:
            doc_id: 文档 ID
            images: 图片列表，每个图片包含 {image_path, caption, page_num}
        """
        with self.get_connection() as conn:
            # 先删除旧图片记录
            conn.execute('DELETE FROM document_images WHERE document_id = ?', (doc_id,))
            
            # 插入新图片
            for idx, img in enumerate(images):
                img_id = f"img_{doc_id}_{idx}"
                conn.execute('''
                    INSERT INTO document_images 
                    (id, document_id, image_index, image_path, caption, page_num)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    img_id,
                    doc_id,
                    idx,
                    img.get('image_path', ''),
                    img.get('caption', ''),
                    img.get('page_num', 0)
                ))
        
        logger.info(f"保存文档图片: {doc_id}, 共 {len(images)} 张")
    
    def get_images_by_document(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        获取文档的所有图片
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            图片列表
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM document_images WHERE document_id = ? ORDER BY image_index',
                (doc_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 历史记录操作 ==========
    
    def save_history(
        self,
        history_id: str,
        topic: str,
        article_type: str,
        target_length: str,
        markdown_content: str,
        outline: str,
        sections_count: int = 0,
        code_blocks_count: int = 0,
        images_count: int = 0,
        review_score: int = 0,
        cover_image: str = None,
        cover_video: str = None,
        target_sections_count: int = None,
        target_images_count: int = None,
        target_code_blocks_count: int = None,
        target_word_count: int = None,
        citations: str = None
    ) -> Dict[str, Any]:
        """保存历史记录"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO history_records 
                (id, topic, article_type, target_length, markdown_content, outline, 
                 sections_count, code_blocks_count, images_count, review_score, cover_image, cover_video,
                 target_sections_count, target_images_count, target_code_blocks_count, target_word_count, citations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                history_id, topic, article_type, target_length, markdown_content, outline,
                sections_count, code_blocks_count, images_count, review_score, cover_image, cover_video,
                target_sections_count, target_images_count, target_code_blocks_count, target_word_count, citations
            ))
        
        logger.info(f"保存历史记录: {history_id}, 主题: {topic}")
        return self.get_history(history_id)
    
    def get_history(self, history_id: str) -> Optional[Dict[str, Any]]:
        """获取单条历史记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM history_records WHERE id = ?',
                (history_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def list_history(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """列出历史记录（按时间倒序，支持分页，包含归属书籍信息）"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''SELECT hr.id, hr.topic, hr.article_type, hr.target_length, hr.sections_count, 
                   hr.code_blocks_count, hr.images_count, hr.review_score, hr.cover_image, hr.cover_video,
                   hr.target_sections_count, hr.target_images_count, hr.target_code_blocks_count, hr.target_word_count,
                   hr.created_at,
                   b.id as book_id,
                   b.title as book_title
                   FROM history_records hr
                   LEFT JOIN book_chapters bc ON hr.id = bc.blog_id
                   LEFT JOIN books b ON bc.book_id = b.id
                   ORDER BY hr.created_at DESC LIMIT ? OFFSET ?''',
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def count_history(self) -> int:
        """获取历史记录总数"""
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM history_records')
            return cursor.fetchone()[0]
    
    def update_history_video(self, history_id: str, cover_video: str) -> bool:
        """更新历史记录的封面动画"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE history_records 
                SET cover_video = ?
                WHERE id = ?
            ''', (cover_video, history_id))
            updated = cursor.rowcount > 0
        
        if updated:
            logger.info(f"更新历史记录封面动画: {history_id}")
        return updated
    
    def delete_history(self, history_id: str) -> bool:
        """删除历史记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'DELETE FROM history_records WHERE id = ?',
                (history_id,)
            )
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"删除历史记录: {history_id}")
        return deleted
    
    # ========== 小红书记录操作 ==========
    
    def list_history_by_type(
        self, 
        content_type: str = None, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按类型列出历史记录
        
        Args:
            content_type: 内容类型 ('blog' | 'xhs' | None表示全部)
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            历史记录列表
        """
        with self.get_connection() as conn:
            if content_type and content_type != 'all':
                cursor = conn.execute(
                    '''SELECT hr.id, hr.topic, hr.article_type, hr.target_length, hr.sections_count, 
                       hr.code_blocks_count, hr.images_count, hr.review_score, hr.cover_image, hr.cover_video,
                       hr.target_sections_count, hr.target_images_count, hr.target_code_blocks_count, hr.target_word_count,
                       hr.created_at, hr.content_type, hr.source_id, hr.derived_ids,
                       hr.xhs_style, hr.xhs_image_urls, hr.xhs_copy_text, hr.xhs_hashtags, hr.xhs_publish_url,
                       hr.publish_platforms,
                       b.id as book_id,
                       b.title as book_title
                       FROM history_records hr
                       LEFT JOIN book_chapters bc ON hr.id = bc.blog_id
                       LEFT JOIN books b ON bc.book_id = b.id
                       WHERE hr.content_type = ? OR (hr.content_type IS NULL AND ? = 'blog')
                       ORDER BY hr.created_at DESC LIMIT ? OFFSET ?''',
                    (content_type, content_type, limit, offset)
                )
            else:
                cursor = conn.execute(
                    '''SELECT hr.id, hr.topic, hr.article_type, hr.target_length, hr.sections_count, 
                       hr.code_blocks_count, hr.images_count, hr.review_score, hr.cover_image, hr.cover_video,
                       hr.target_sections_count, hr.target_images_count, hr.target_code_blocks_count, hr.target_word_count,
                       hr.created_at, hr.content_type, hr.source_id, hr.derived_ids,
                       hr.xhs_style, hr.xhs_image_urls, hr.xhs_copy_text, hr.xhs_hashtags, hr.xhs_publish_url,
                       hr.publish_platforms,
                       b.id as book_id,
                       b.title as book_title
                       FROM history_records hr
                       LEFT JOIN book_chapters bc ON hr.id = bc.blog_id
                       LEFT JOIN books b ON bc.book_id = b.id
                       ORDER BY hr.created_at DESC LIMIT ? OFFSET ?''',
                    (limit, offset)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def count_history_by_type(self, content_type: str = None) -> int:
        """
        按类型统计历史记录数量
        
        Args:
            content_type: 内容类型 ('blog' | 'xhs' | None表示全部)
        
        Returns:
            记录数量
        """
        with self.get_connection() as conn:
            if content_type and content_type != 'all':
                cursor = conn.execute(
                    '''SELECT COUNT(*) FROM history_records 
                       WHERE content_type = ? OR (content_type IS NULL AND ? = 'blog')''',
                    (content_type, content_type)
                )
            else:
                cursor = conn.execute('SELECT COUNT(*) FROM history_records')
            return cursor.fetchone()[0]
    
    def save_xhs_record(
        self,
        history_id: str,
        topic: str,
        style: str = "hand_drawn",
        layout_type: str = "list",
        image_urls: list = None,
        copy_text: str = "",
        hashtags: list = None,
        cover_image: str = None,
        cover_video: str = None,
        source_id: str = None
    ) -> Dict[str, Any]:
        """
        保存小红书记录
        
        Args:
            history_id: 记录ID
            topic: 主题
            style: 风格 (hand_drawn | claymation)
            layout_type: 布局类型
            image_urls: 图片URL列表
            copy_text: 小红书文案
            hashtags: 话题标签列表
            cover_image: 封面图
            cover_video: 封面视频
            source_id: 来源博客ID（如果是从博客转换的）
        
        Returns:
            创建的记录
        """
        import json
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO history_records 
                (id, topic, content_type, xhs_style, xhs_layout_type, 
                 xhs_image_urls, xhs_copy_text, xhs_hashtags, 
                 cover_image, cover_video, source_id, images_count)
                VALUES (?, ?, 'xhs', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                history_id, topic, style, layout_type,
                json.dumps(image_urls or [], ensure_ascii=False),
                copy_text,
                json.dumps(hashtags or [], ensure_ascii=False),
                cover_image, cover_video, source_id,
                len(image_urls or [])
            ))
        
        # 如果有来源记录，更新其 derived_ids
        if source_id:
            self._add_derived_id(source_id, history_id)
        
        logger.info(f"保存小红书记录: {history_id}, 主题: {topic}")
        return self.get_history(history_id)
    
    def _add_derived_id(self, source_id: str, derived_id: str):
        """添加衍生记录ID到来源记录"""
        import json
        record = self.get_history(source_id)
        if record:
            derived_ids = json.loads(record.get('derived_ids') or '[]')
            if derived_id not in derived_ids:
                derived_ids.append(derived_id)
                with self.get_connection() as conn:
                    conn.execute('''
                        UPDATE history_records 
                        SET derived_ids = ?
                        WHERE id = ?
                    ''', (json.dumps(derived_ids), source_id))
    
    def update_publish_platforms(self, history_id: str, platform: str, status: dict) -> bool:
        """
        更新多平台发布状态
        
        Args:
            history_id: 记录ID
            platform: 平台名称 (csdn | zhihu | juejin | xiaohongshu)
            status: 状态信息 {status, url, published_at}
        
        Returns:
            是否更新成功
        """
        import json
        record = self.get_history(history_id)
        if record:
            platforms = json.loads(record.get('publish_platforms') or '{}')
            platforms[platform] = status
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    UPDATE history_records 
                    SET publish_platforms = ?
                    WHERE id = ?
                ''', (json.dumps(platforms, ensure_ascii=False), history_id))
                return cursor.rowcount > 0
        return False
    
    def update_xhs_publish_url(self, history_id: str, publish_url: str) -> bool:
        """更新小红书发布链接"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE history_records 
                SET xhs_publish_url = ?
                WHERE id = ?
            ''', (publish_url, history_id))
            return cursor.rowcount > 0
    
    def update_history_summary(self, history_id: str, summary: str) -> bool:
        """
        更新博客摘要
        
        Args:
            history_id: 博客 ID
            summary: 博客摘要
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE history_records 
                SET summary = ?
                WHERE id = ?
            ''', (summary, history_id))
            updated = cursor.rowcount > 0
        
        if updated:
            logger.info(f"更新博客摘要: {history_id}")
        return updated
    
    def update_history_book_id(self, history_id: str, book_id: str) -> bool:
        """
        更新博客所属书籍
        
        Args:
            history_id: 博客 ID
            book_id: 书籍 ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE history_records 
                SET book_id = ?
                WHERE id = ?
            ''', (book_id, history_id))
            return cursor.rowcount > 0
    
    # ========== 书籍操作 ==========
    
    def create_book(
        self,
        book_id: str,
        title: str,
        theme: str = 'general',
        description: str = None
    ) -> Dict[str, Any]:
        """
        创建书籍记录
        
        Args:
            book_id: 书籍 ID
            title: 书籍标题
            theme: 主题分类
            description: 书籍描述
        
        Returns:
            创建的书籍记录
        """
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO books (id, title, theme, description)
                VALUES (?, ?, ?, ?)
            ''', (book_id, title, theme, description))
        
        logger.info(f"创建书籍: {book_id}, {title}")
        return self.get_book(book_id)
    
    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        """获取书籍记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM books WHERE id = ?',
                (book_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def list_books(self, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
        """列出书籍"""
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    'SELECT * FROM books WHERE status = ? ORDER BY updated_at DESC LIMIT ?',
                    (status, limit)
                )
            else:
                cursor = conn.execute(
                    'SELECT * FROM books ORDER BY updated_at DESC LIMIT ?',
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_book(
        self,
        book_id: str,
        title: str = None,
        description: str = None,
        theme: str = None,
        cover_image: str = None,
        outline: str = None,
        chapters_count: int = None,
        total_word_count: int = None,
        blogs_count: int = None,
        status: str = None
    ) -> bool:
        """更新书籍信息"""
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if theme is not None:
            updates.append("theme = ?")
            params.append(theme)
        if cover_image is not None:
            updates.append("cover_image = ?")
            params.append(cover_image)
        if outline is not None:
            updates.append("outline = ?")
            params.append(outline)
        if chapters_count is not None:
            updates.append("chapters_count = ?")
            params.append(chapters_count)
        if total_word_count is not None:
            updates.append("total_word_count = ?")
            params.append(total_word_count)
        if blogs_count is not None:
            updates.append("blogs_count = ?")
            params.append(blogs_count)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(book_id)
        
        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE books SET {', '.join(updates)} WHERE id = ?",
                params
            )
            updated = cursor.rowcount > 0
        
        if updated:
            logger.info(f"更新书籍: {book_id}")
        return updated
    
    def delete_book(self, book_id: str) -> bool:
        """删除书籍"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'DELETE FROM books WHERE id = ?',
                (book_id,)
            )
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"删除书籍: {book_id}")
        return deleted
    
    def update_book_homepage(self, book_id: str, homepage_content: dict) -> bool:
        """
        更新书籍首页内容
        
        Args:
            book_id: 书籍 ID
            homepage_content: 首页内容字典，包含 slogan, introduction, highlights, target_audience, prerequisites
        """
        import json
        
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE books SET 
                    homepage_content = ?,
                    highlights = ?,
                    target_audience = ?,
                    prerequisites = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?''',
                (
                    json.dumps(homepage_content, ensure_ascii=False),
                    json.dumps(homepage_content.get('highlights', []), ensure_ascii=False),
                    json.dumps(homepage_content.get('target_audience', []), ensure_ascii=False),
                    json.dumps(homepage_content.get('prerequisites', []), ensure_ascii=False),
                    book_id
                )
            )
            updated = cursor.rowcount > 0
        
        if updated:
            logger.info(f"更新书籍首页: {book_id}")
        return updated
    
    def update_book_full_outline(self, book_id: str, full_outline: dict) -> bool:
        """
        更新书籍完整大纲（包含待建设章节）
        
        Args:
            book_id: 书籍 ID
            full_outline: 完整大纲字典
        """
        import json
        
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE books SET 
                    full_outline = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?''',
                (json.dumps(full_outline, ensure_ascii=False), book_id)
            )
            updated = cursor.rowcount > 0
        
        if updated:
            logger.info(f"更新书籍完整大纲: {book_id}")
        return updated
    
    # ========== 书籍章节操作 ==========
    
    def save_book_chapters(self, book_id: str, chapters: List[Dict[str, Any]]):
        """
        保存书籍章节结构
        
        Args:
            book_id: 书籍 ID
            chapters: 章节列表，每个章节包含 {chapter_index, chapter_title, section_index, section_title, blog_id, has_content, word_count}
        """
        with self.get_connection() as conn:
            # 先删除旧章节
            conn.execute('DELETE FROM book_chapters WHERE book_id = ?', (book_id,))
            
            # 插入新章节
            for idx, chapter in enumerate(chapters):
                chapter_id = f"chapter_{book_id}_{idx}"
                conn.execute('''
                    INSERT INTO book_chapters 
                    (id, book_id, chapter_index, chapter_title, section_index, section_title, blog_id, has_content, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chapter_id,
                    book_id,
                    chapter.get('chapter_index', 0),
                    chapter.get('chapter_title', ''),
                    chapter.get('section_index', ''),
                    chapter.get('section_title', ''),
                    chapter.get('blog_id'),
                    1 if chapter.get('blog_id') else 0,
                    chapter.get('word_count', 0)
                ))
        
        logger.info(f"保存书籍章节: {book_id}, 共 {len(chapters)} 个章节")
    
    def get_book_chapters(self, book_id: str) -> List[Dict[str, Any]]:
        """获取书籍的所有章节"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM book_chapters WHERE book_id = ? ORDER BY chapter_index, section_index',
                (book_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_chapter_with_content(self, book_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        """获取章节及其关联的博客内容"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT bc.*, hr.markdown_content, hr.topic as blog_topic
                FROM book_chapters bc
                LEFT JOIN history_records hr ON bc.blog_id = hr.id
                WHERE bc.book_id = ? AND bc.id = ?
            ''', (book_id, chapter_id))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_blogs_by_book(self, book_id: str) -> List[Dict[str, Any]]:
        """获取书籍关联的所有博客"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT hr.* FROM history_records hr
                INNER JOIN book_chapters bc ON hr.id = bc.blog_id
                WHERE bc.book_id = ?
                ORDER BY bc.chapter_index, bc.section_index
            ''', (book_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unassigned_blogs(self) -> List[Dict[str, Any]]:
        """获取未分配到任何书籍的博客"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT hr.* FROM history_records hr
                WHERE hr.book_id IS NULL
                ORDER BY hr.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_blogs_with_book_info(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有博客及其所属书籍信息"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT hr.*, 
                       bc.book_id,
                       bc.chapter_index,
                       bc.chapter_title,
                       bc.section_index,
                       bc.section_title,
                       b.title as book_title
                FROM history_records hr
                LEFT JOIN book_chapters bc ON hr.id = bc.blog_id
                LEFT JOIN books b ON bc.book_id = b.id
                ORDER BY hr.created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]


    def clear_all_books(self):
        """
        清空所有书籍数据（用于重新生成）
        
        删除 books 和 book_chapters 表的所有数据
        """
        with self.get_connection() as conn:
            conn.execute('DELETE FROM book_chapters')
            conn.execute('DELETE FROM books')
        logger.info("已清空所有书籍数据")
    
    def reset_all_blog_book_ids(self):
        """
        重置所有博客的 book_id 为 NULL（用于重新生成）
        """
        with self.get_connection() as conn:
            conn.execute('UPDATE history_records SET book_id = NULL')
        logger.info("已重置所有博客的 book_id")


# 全局单例
_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """获取数据库服务单例"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


def init_db_service(db_path: str = None) -> DatabaseService:
    """初始化数据库服务"""
    global _db_service
    _db_service = DatabaseService(db_path)
    return _db_service
