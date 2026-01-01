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
        """
        if db_path is None:
            # 默认路径: backend/data/banana_blog.db
            base_dir = Path(__file__).parent.parent
            db_path = str(base_dir / "data" / "banana_blog.db")
        
        self.db_path = db_path
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # 初始化表
        self._init_tables()
        logger.info(f"数据库服务已初始化: {db_path}")
    
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
                    mineru_folder TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parsed_at TIMESTAMP
                );
                
                -- 创建索引
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
            ''')
        logger.info("数据库表初始化完成")
    
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
