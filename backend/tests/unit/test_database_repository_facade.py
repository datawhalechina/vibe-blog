import inspect

import pytest

from repositories.database import (
    BookRepository,
    DocumentRepository,
    HistoryRepository,
    SQLiteRuntime,
)
from services.database_service import DatabaseService


PUBLIC_SIGNATURES = {
    "get_connection": "(self)",
    "create_document": "(self, doc_id: str, filename: str, file_path: str, file_size: int, file_type: str) -> Dict[str, Any]",
    "get_document": "(self, doc_id: str) -> Optional[Dict[str, Any]]",
    "update_document_status": "(self, doc_id: str, status: str, error_message: str = None)",
    "save_parse_result": "(self, doc_id: str, markdown: str, mineru_folder: str = None)",
    "get_documents_by_ids": "(self, doc_ids: List[str]) -> List[Dict[str, Any]]",
    "delete_document": "(self, doc_id: str) -> bool",
    "list_documents": "(self, status: str = None, limit: int = 50) -> List[Dict[str, Any]]",
    "update_document_summary": "(self, doc_id: str, summary: str)",
    "save_chunks": "(self, doc_id: str, chunks: List[Dict[str, Any]])",
    "get_chunks_by_document": "(self, doc_id: str) -> List[Dict[str, Any]]",
    "get_chunks_by_documents": "(self, doc_ids: List[str]) -> List[Dict[str, Any]]",
    "save_images": "(self, doc_id: str, images: List[Dict[str, Any]])",
    "get_images_by_document": "(self, doc_id: str) -> List[Dict[str, Any]]",
    "save_history": "(self, history_id: str, topic: str, article_type: str, target_length: str, markdown_content: str, outline: str, sections_count: int = 0, code_blocks_count: int = 0, images_count: int = 0, review_score: int = 0, cover_image: str = None, cover_video: str = None, target_sections_count: int = None, target_images_count: int = None, target_code_blocks_count: int = None, target_word_count: int = None, citations: str = None) -> Dict[str, Any]",
    "get_history": "(self, history_id: str) -> Optional[Dict[str, Any]]",
    "list_history": "(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]",
    "count_history": "(self) -> int",
    "update_history_video": "(self, history_id: str, cover_video: str) -> bool",
    "delete_history": "(self, history_id: str) -> bool",
    "list_history_by_type": "(self, content_type: str = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]",
    "count_history_by_type": "(self, content_type: str = None) -> int",
    "save_xhs_record": "(self, history_id: str, topic: str, style: str = 'hand_drawn', layout_type: str = 'list', image_urls: list = None, copy_text: str = '', hashtags: list = None, cover_image: str = None, cover_video: str = None, source_id: str = None) -> Dict[str, Any]",
    "update_publish_platforms": "(self, history_id: str, platform: str, status: dict) -> bool",
    "update_xhs_publish_url": "(self, history_id: str, publish_url: str) -> bool",
    "update_history_summary": "(self, history_id: str, summary: str) -> bool",
    "update_history_markdown": "(self, history_id: str, markdown_content: str) -> bool",
    "update_history_book_id": "(self, history_id: str, book_id: str) -> bool",
    "create_book": "(self, book_id: str, title: str, theme: str = 'general', description: str = None) -> Dict[str, Any]",
    "get_book": "(self, book_id: str) -> Optional[Dict[str, Any]]",
    "list_books": "(self, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]",
    "update_book": "(self, book_id: str, title: str = None, description: str = None, theme: str = None, cover_image: str = None, outline: str = None, chapters_count: int = None, total_word_count: int = None, blogs_count: int = None, status: str = None) -> bool",
    "delete_book": "(self, book_id: str) -> bool",
    "update_book_homepage": "(self, book_id: str, homepage_content: dict) -> bool",
    "update_book_full_outline": "(self, book_id: str, full_outline: dict) -> bool",
    "save_book_chapters": "(self, book_id: str, chapters: List[Dict[str, Any]])",
    "get_book_chapters": "(self, book_id: str) -> List[Dict[str, Any]]",
    "get_chapter_with_content": "(self, book_id: str, chapter_id: str) -> Optional[Dict[str, Any]]",
    "get_blogs_by_book": "(self, book_id: str) -> List[Dict[str, Any]]",
    "get_unassigned_blogs": "(self) -> List[Dict[str, Any]]",
    "get_all_blogs_with_book_info": "(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]",
    "clear_all_books": "(self)",
    "reset_all_blog_book_ids": "(self)",
}


def test_database_service_preserves_public_method_signatures():
    actual = {
        name: str(inspect.signature(value))
        for name, value in DatabaseService.__dict__.items()
        if callable(value) and not name.startswith("_")
    }

    assert actual == PUBLIC_SIGNATURES


def test_database_service_preserves_private_compatibility_signatures():
    expected = {
        "__init__": "(self, db_path: str = None)",
        "_init_tables": "(self)",
        "_migrate_tables": "(self)",
        "_add_derived_id": "(self, source_id: str, derived_id: str)",
    }

    assert {
        name: str(inspect.signature(DatabaseService.__dict__[name]))
        for name in expected
    } == expected


def test_database_service_uses_one_runtime_for_all_repositories(tmp_path):
    service = DatabaseService(str(tmp_path / "database.db"))

    assert isinstance(service._runtime, SQLiteRuntime)
    assert isinstance(service.documents, DocumentRepository)
    assert isinstance(service.history, HistoryRepository)
    assert isinstance(service.books, BookRepository)
    assert service.documents.runtime is service._runtime
    assert service.history.runtime is service._runtime
    assert service.books.runtime is service._runtime
    assert service.db_path == service._runtime.db_path


def test_database_service_connection_override_intercepts_repository_work(
    tmp_path, monkeypatch
):
    service = DatabaseService(str(tmp_path / "database.db"))
    original_get_connection = service.get_connection
    calls = []

    def tracking_get_connection():
        calls.append(True)
        return original_get_connection()

    monkeypatch.setattr(service, "get_connection", tracking_get_connection)

    service.create_document("doc-1", "guide.pdf", "/tmp/guide.pdf", 42, "pdf")

    assert len(calls) == 2


def test_database_service_migration_override_runs_during_initialization(tmp_path):
    class TrackingDatabaseService(DatabaseService):
        def _migrate_tables(self):
            self.migration_calls = getattr(self, "migration_calls", 0) + 1
            return super()._migrate_tables()

    service = TrackingDatabaseService(str(tmp_path / "database.db"))

    assert service.migration_calls == 1


def test_repositories_share_data_with_the_compatibility_facade(tmp_path):
    service = DatabaseService(str(tmp_path / "database.db"))

    service.documents.create_document(
        "doc-1", "guide.pdf", "/tmp/guide.pdf", 42, "pdf"
    )
    service.history.save_history(
        "history-1", "Repository extraction", "tutorial", "medium", "# Body", "{}"
    )
    service.books.create_book("book-1", "Architecture Guide")

    assert service.get_document("doc-1")["filename"] == "guide.pdf"
    assert service.get_history("history-1")["topic"] == "Repository extraction"
    assert service.get_book("book-1")["title"] == "Architecture Guide"


@pytest.mark.parametrize(
    ("repository_name", "method_name", "args", "kwargs", "forwarded_args"),
    [
        (
            "documents",
            "create_document",
            ("doc-1", "guide.pdf", "/tmp/guide.pdf", 42, "pdf"),
            {},
            ("doc-1", "guide.pdf", "/tmp/guide.pdf", 42, "pdf"),
        ),
        (
            "history",
            "list_history_by_type",
            (),
            {"content_type": "blog", "limit": 7, "offset": 3},
            ("blog", 7, 3),
        ),
        (
            "books",
            "update_book",
            ("book-1",),
            {"title": "New title", "status": "active"},
            ("book-1", "New title", None, None, None, None, None, None, None, "active"),
        ),
    ],
)
def test_database_service_delegates_with_unchanged_arguments(
    tmp_path,
    monkeypatch,
    repository_name,
    method_name,
    args,
    kwargs,
    forwarded_args,
):
    service = DatabaseService(str(tmp_path / "database.db"))
    repository = getattr(service, repository_name)
    calls = []
    expected = object()

    def fake_method(*received_args, **received_kwargs):
        calls.append((received_args, received_kwargs))
        return expected

    monkeypatch.setattr(repository, method_name, fake_method)

    assert getattr(service, method_name)(*args, **kwargs) is expected
    assert calls == [(forwarded_args, {})]


def test_runtime_commits_successful_transactions(tmp_path):
    runtime = SQLiteRuntime(str(tmp_path / "database.db"))
    runtime.initialize()

    with runtime.get_connection() as connection:
        connection.execute(
            "INSERT INTO books (id, title) VALUES (?, ?)",
            ("book-1", "Committed"),
        )

    with runtime.get_connection() as connection:
        title = connection.execute(
            "SELECT title FROM books WHERE id = ?", ("book-1",)
        ).fetchone()[0]

    assert title == "Committed"


def test_runtime_rolls_back_failed_transactions(tmp_path):
    runtime = SQLiteRuntime(str(tmp_path / "database.db"))
    runtime.initialize()

    with pytest.raises(RuntimeError, match="abort"):
        with runtime.get_connection() as connection:
            connection.execute(
                "INSERT INTO books (id, title) VALUES (?, ?)",
                ("book-1", "Rolled back"),
            )
            raise RuntimeError("abort")

    with runtime.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM books WHERE id = ?", ("book-1",)
        ).fetchone()[0]

    assert count == 0


def test_runtime_initialization_and_migrations_are_idempotent(tmp_path):
    db_path = str(tmp_path / "database.db")
    SQLiteRuntime(db_path).initialize()
    SQLiteRuntime(db_path).initialize()

    with SQLiteRuntime(db_path).get_connection() as connection:
        history_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(history_records)")
        }
        book_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(books)")
        }

    assert {"content_type", "publish_platforms", "book_id"} <= history_columns
    assert {"homepage_content", "full_outline", "highlights"} <= book_columns
