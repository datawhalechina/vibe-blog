"""Compatibility facade for application persistence repositories."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from repositories.database import (
    BookRepository,
    DocumentRepository,
    HistoryRepository,
    SQLiteRuntime,
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Preserve the historical database API while delegating persistence."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_path = str(base_dir / "data" / "banana_blog.db")

        self._runtime = SQLiteRuntime(db_path)
        self.db_path = self._runtime.db_path
        self.documents = DocumentRepository(self._runtime, connection_provider=self)
        self.history = HistoryRepository(self._runtime, connection_provider=self)
        self.books = BookRepository(self._runtime, connection_provider=self)
        self._init_tables()
        logger.info(f"数据库服务已初始化: {self.db_path}")

    def get_connection(self):
        return self._runtime.get_connection()

    def _init_tables(self):
        return self._runtime.initialize(
            connection_provider=self,
            migration_callback=self._migrate_tables,
        )

    def _migrate_tables(self):
        return self._runtime.migrate(connection_provider=self)

    def create_document(
        self,
        doc_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str
    ) -> Dict[str, Any]:
        return self.documents.create_document(doc_id, filename, file_path, file_size, file_type)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.documents.get_document(doc_id)

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        error_message: str = None
    ):
        return self.documents.update_document_status(doc_id, status, error_message)

    def save_parse_result(
        self,
        doc_id: str,
        markdown: str,
        mineru_folder: str = None
    ):
        return self.documents.save_parse_result(doc_id, markdown, mineru_folder)

    def get_documents_by_ids(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        return self.documents.get_documents_by_ids(doc_ids)

    def delete_document(self, doc_id: str) -> bool:
        return self.documents.delete_document(doc_id)

    def list_documents(
        self,
        status: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return self.documents.list_documents(status, limit)

    def update_document_summary(self, doc_id: str, summary: str):
        return self.documents.update_document_summary(doc_id, summary)

    def save_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]):
        return self.documents.save_chunks(doc_id, chunks)

    def get_chunks_by_document(self, doc_id: str) -> List[Dict[str, Any]]:
        return self.documents.get_chunks_by_document(doc_id)

    def get_chunks_by_documents(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        return self.documents.get_chunks_by_documents(doc_ids)

    def save_images(self, doc_id: str, images: List[Dict[str, Any]]):
        return self.documents.save_images(doc_id, images)

    def get_images_by_document(self, doc_id: str) -> List[Dict[str, Any]]:
        return self.documents.get_images_by_document(doc_id)

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
        return self.history.save_history(history_id, topic, article_type, target_length, markdown_content, outline, sections_count, code_blocks_count, images_count, review_score, cover_image, cover_video, target_sections_count, target_images_count, target_code_blocks_count, target_word_count, citations)

    def get_history(self, history_id: str) -> Optional[Dict[str, Any]]:
        return self.history.get_history(history_id)

    def list_history(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        return self.history.list_history(limit, offset)

    def count_history(self) -> int:
        return self.history.count_history()

    def update_history_video(self, history_id: str, cover_video: str) -> bool:
        return self.history.update_history_video(history_id, cover_video)

    def delete_history(self, history_id: str) -> bool:
        return self.history.delete_history(history_id)

    def list_history_by_type(
        self,
        content_type: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        return self.history.list_history_by_type(content_type, limit, offset)

    def count_history_by_type(self, content_type: str = None) -> int:
        return self.history.count_history_by_type(content_type)

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
        return self.history.save_xhs_record(history_id, topic, style, layout_type, image_urls, copy_text, hashtags, cover_image, cover_video, source_id)

    def _add_derived_id(self, source_id: str, derived_id: str):
        return self.history._add_derived_id(source_id, derived_id)

    def update_publish_platforms(self, history_id: str, platform: str, status: dict) -> bool:
        return self.history.update_publish_platforms(history_id, platform, status)

    def update_xhs_publish_url(self, history_id: str, publish_url: str) -> bool:
        return self.history.update_xhs_publish_url(history_id, publish_url)

    def update_history_summary(self, history_id: str, summary: str) -> bool:
        return self.history.update_history_summary(history_id, summary)

    def update_history_markdown(self, history_id: str, markdown_content: str) -> bool:
        return self.history.update_history_markdown(history_id, markdown_content)

    def update_history_book_id(self, history_id: str, book_id: str) -> bool:
        return self.history.update_history_book_id(history_id, book_id)

    def create_book(
        self,
        book_id: str,
        title: str,
        theme: str = 'general',
        description: str = None
    ) -> Dict[str, Any]:
        return self.books.create_book(book_id, title, theme, description)

    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        return self.books.get_book(book_id)

    def list_books(self, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
        return self.books.list_books(status, limit)

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
        return self.books.update_book(book_id, title, description, theme, cover_image, outline, chapters_count, total_word_count, blogs_count, status)

    def delete_book(self, book_id: str) -> bool:
        return self.books.delete_book(book_id)

    def update_book_homepage(self, book_id: str, homepage_content: dict) -> bool:
        return self.books.update_book_homepage(book_id, homepage_content)

    def update_book_full_outline(self, book_id: str, full_outline: dict) -> bool:
        return self.books.update_book_full_outline(book_id, full_outline)

    def save_book_chapters(self, book_id: str, chapters: List[Dict[str, Any]]):
        return self.books.save_book_chapters(book_id, chapters)

    def get_book_chapters(self, book_id: str) -> List[Dict[str, Any]]:
        return self.books.get_book_chapters(book_id)

    def get_chapter_with_content(self, book_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        return self.books.get_chapter_with_content(book_id, chapter_id)

    def get_blogs_by_book(self, book_id: str) -> List[Dict[str, Any]]:
        return self.books.get_blogs_by_book(book_id)

    def get_unassigned_blogs(self) -> List[Dict[str, Any]]:
        return self.books.get_unassigned_blogs()

    def get_all_blogs_with_book_info(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return self.books.get_all_blogs_with_book_info(limit, offset)

    def clear_all_books(self):
        return self.books.clear_all_books()

    def reset_all_blog_book_ids(self):
        return self.books.reset_all_blog_book_ids()


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
