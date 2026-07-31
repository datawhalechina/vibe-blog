"""Document, chunk, and image persistence."""

import logging
from typing import Any, Dict, List, Optional

from .runtime import SQLiteRuntime

logger = logging.getLogger("services.database_service")


class DocumentRepository:
    def __init__(self, runtime: SQLiteRuntime, connection_provider=None):
        self.runtime = runtime
        self._connection_provider = connection_provider or runtime

    def get_connection(self):
        return self._connection_provider.get_connection()

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
