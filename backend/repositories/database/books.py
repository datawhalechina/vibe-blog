"""Book, chapter, and blog assignment persistence."""

import logging
from typing import Any, Dict, List, Optional

from .runtime import SQLiteRuntime

logger = logging.getLogger("services.database_service")


class BookRepository:
    def __init__(self, runtime: SQLiteRuntime, connection_provider=None):
        self.runtime = runtime
        self._connection_provider = connection_provider or runtime

    def get_connection(self):
        return self._connection_provider.get_connection()

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
