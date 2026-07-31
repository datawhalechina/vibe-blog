"""Generated-content history and publishing persistence."""

import logging
from typing import Any, Dict, List, Optional

from .runtime import SQLiteRuntime

logger = logging.getLogger("services.database_service")


class HistoryRepository:
    def __init__(self, runtime: SQLiteRuntime, connection_provider=None):
        self.runtime = runtime
        self._connection_provider = connection_provider or runtime

    def get_connection(self):
        return self._connection_provider.get_connection()

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

    def update_history_markdown(self, history_id: str, markdown_content: str) -> bool:
        """
        更新博客正文 Markdown

        Args:
            history_id: 博客 ID
            markdown_content: 最新 Markdown 内容
        """
        with self.get_connection() as conn:
            cursor = conn.execute('''
                UPDATE history_records
                SET markdown_content = ?
                WHERE id = ?
            ''', (markdown_content, history_id))
            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"更新博客正文: {history_id}, 长度={len(markdown_content)}")
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
