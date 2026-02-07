"""
DatabaseService 单元测试
测试数据库服务的核心功能：文档管理、历史记录管理
"""
import pytest
import uuid
from services.database_service import DatabaseService


@pytest.fixture
def db_service():
    """创建内存数据库服务实例"""
    # 使用临时文件而不是内存数据库，避免迁移问题
    import tempfile
    import os

    # 创建临时数据库文件
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        service = DatabaseService(db_path)
        yield service
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def sample_doc_id():
    """生成测试文档 ID"""
    return f"test_doc_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_history_id():
    """生成测试历史记录 ID"""
    return f"test_history_{uuid.uuid4().hex[:8]}"


# ========== 文档操作测试 ==========

@pytest.mark.unit
class TestDocumentOperations:
    """文档操作测试"""

    def test_create_document(self, db_service, sample_doc_id):
        """测试创建文档记录"""
        doc = db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        assert doc is not None
        assert doc['id'] == sample_doc_id
        assert doc['filename'] == "test.pdf"
        assert doc['file_size'] == 1024
        assert doc['file_type'] == "pdf"
        assert doc['status'] == 'pending'

    def test_get_document(self, db_service, sample_doc_id):
        """测试获取文档记录"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 获取文档
        doc = db_service.get_document(sample_doc_id)
        assert doc is not None
        assert doc['id'] == sample_doc_id

    def test_get_nonexistent_document(self, db_service):
        """测试获取不存在的文档"""
        doc = db_service.get_document("nonexistent_id")
        assert doc is None

    def test_update_document_status(self, db_service, sample_doc_id):
        """测试更新文档状态"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 更新状态
        db_service.update_document_status(sample_doc_id, "parsing")
        doc = db_service.get_document(sample_doc_id)
        assert doc['status'] == 'parsing'

        # 更新为错误状态
        db_service.update_document_status(sample_doc_id, "error", "Parse failed")
        doc = db_service.get_document(sample_doc_id)
        assert doc['status'] == 'error'
        assert doc['error_message'] == "Parse failed"

    def test_save_parse_result(self, db_service, sample_doc_id):
        """测试保存解析结果"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 保存解析结果
        markdown = "# Test Document\n\nThis is a test."
        db_service.save_parse_result(sample_doc_id, markdown, "/tmp/mineru")

        doc = db_service.get_document(sample_doc_id)
        assert doc['status'] == 'ready'
        assert doc['markdown_content'] == markdown
        assert doc['markdown_length'] == len(markdown)
        assert doc['mineru_folder'] == "/tmp/mineru"
        assert doc['parsed_at'] is not None

    def test_delete_document(self, db_service, sample_doc_id):
        """测试删除文档"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 删除文档
        result = db_service.delete_document(sample_doc_id)
        assert result is True

        # 验证已删除
        doc = db_service.get_document(sample_doc_id)
        assert doc is None

    def test_delete_nonexistent_document(self, db_service):
        """测试删除不存在的文档"""
        result = db_service.delete_document("nonexistent_id")
        assert result is False

    def test_list_documents(self, db_service):
        """测试列出文档"""
        # 创建多个文档
        for i in range(3):
            db_service.create_document(
                doc_id=f"doc_{i}",
                filename=f"test_{i}.pdf",
                file_path=f"/tmp/test_{i}.pdf",
                file_size=1024 * (i + 1),
                file_type="pdf"
            )

        # 列出所有文档
        docs = db_service.list_documents()
        assert len(docs) == 3

        # 按状态筛选
        docs = db_service.list_documents(status='pending')
        assert len(docs) == 3

        # 限制数量
        docs = db_service.list_documents(limit=2)
        assert len(docs) == 2

    def test_get_documents_by_ids(self, db_service):
        """测试批量获取文档"""
        # 创建文档并设置为 ready
        doc_ids = []
        for i in range(3):
            doc_id = f"doc_{i}"
            doc_ids.append(doc_id)
            db_service.create_document(
                doc_id=doc_id,
                filename=f"test_{i}.pdf",
                file_path=f"/tmp/test_{i}.pdf",
                file_size=1024,
                file_type="pdf"
            )
            db_service.save_parse_result(doc_id, f"# Document {i}")

        # 批量获取
        docs = db_service.get_documents_by_ids(doc_ids)
        assert len(docs) == 3

        # 空列表
        docs = db_service.get_documents_by_ids([])
        assert len(docs) == 0

    def test_update_document_summary(self, db_service, sample_doc_id):
        """测试更新文档摘要"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 更新摘要
        summary = "This is a test document summary."
        db_service.update_document_summary(sample_doc_id, summary)

        doc = db_service.get_document(sample_doc_id)
        assert doc['summary'] == summary


# ========== 历史记录操作测试 ==========

@pytest.mark.unit
class TestHistoryOperations:
    """历史记录操作测试"""

    def test_save_history(self, db_service, sample_history_id):
        """测试保存历史记录"""
        history = db_service.save_history(
            history_id=sample_history_id,
            topic="Test Topic",
            article_type="tutorial",
            target_length="medium",
            markdown_content="# Test Content",
            outline='{"title": "Test"}',
            sections_count=3,
            code_blocks_count=2,
            images_count=1,
            review_score=85,
            cover_image="https://example.com/cover.jpg",
            cover_video="https://example.com/cover.mp4"
        )

        assert history is not None
        assert history['id'] == sample_history_id
        assert history['topic'] == "Test Topic"
        assert history['article_type'] == "tutorial"
        assert history['sections_count'] == 3
        assert history['code_blocks_count'] == 2
        assert history['images_count'] == 1
        assert history['review_score'] == 85

    def test_get_history(self, db_service, sample_history_id):
        """测试获取历史记录"""
        # 保存历史记录
        db_service.save_history(
            history_id=sample_history_id,
            topic="Test Topic",
            article_type="tutorial",
            target_length="medium",
            markdown_content="# Test Content",
            outline='{"title": "Test"}'
        )

        # 获取历史记录
        history = db_service.get_history(sample_history_id)
        assert history is not None
        assert history['id'] == sample_history_id
        assert history['topic'] == "Test Topic"

    def test_get_nonexistent_history(self, db_service):
        """测试获取不存在的历史记录"""
        history = db_service.get_history("nonexistent_id")
        assert history is None

    def test_list_history(self, db_service):
        """测试列出历史记录"""
        # 创建多条历史记录
        for i in range(5):
            db_service.save_history(
                history_id=f"history_{i}",
                topic=f"Topic {i}",
                article_type="tutorial",
                target_length="medium",
                markdown_content=f"# Content {i}",
                outline='{}'
            )

        # 列出所有记录
        records = db_service.list_history(limit=10)
        assert len(records) == 5

        # 测试分页
        records = db_service.list_history(limit=3, offset=0)
        assert len(records) == 3

        records = db_service.list_history(limit=3, offset=3)
        assert len(records) == 2

    def test_count_history(self, db_service):
        """测试统计历史记录数量"""
        # 初始为 0
        count = db_service.count_history()
        assert count == 0

        # 创建记录
        for i in range(3):
            db_service.save_history(
                history_id=f"history_{i}",
                topic=f"Topic {i}",
                article_type="tutorial",
                target_length="medium",
                markdown_content=f"# Content {i}",
                outline='{}'
            )

        count = db_service.count_history()
        assert count == 3

    def test_update_history_video(self, db_service, sample_history_id):
        """测试更新历史记录封面视频"""
        # 保存历史记录
        db_service.save_history(
            history_id=sample_history_id,
            topic="Test Topic",
            article_type="tutorial",
            target_length="medium",
            markdown_content="# Test Content",
            outline='{}'
        )

        # 更新封面视频
        video_url = "https://example.com/new_video.mp4"
        result = db_service.update_history_video(sample_history_id, video_url)
        assert result is True

        history = db_service.get_history(sample_history_id)
        assert history['cover_video'] == video_url

    def test_update_nonexistent_history_video(self, db_service):
        """测试更新不存在的历史记录视频"""
        result = db_service.update_history_video("nonexistent_id", "https://example.com/video.mp4")
        assert result is False

    def test_delete_history(self, db_service, sample_history_id):
        """测试删除历史记录"""
        # 保存历史记录
        db_service.save_history(
            history_id=sample_history_id,
            topic="Test Topic",
            article_type="tutorial",
            target_length="medium",
            markdown_content="# Test Content",
            outline='{}'
        )

        # 删除记录
        result = db_service.delete_history(sample_history_id)
        assert result is True

        # 验证已删除
        history = db_service.get_history(sample_history_id)
        assert history is None

    def test_delete_nonexistent_history(self, db_service):
        """测试删除不存在的历史记录"""
        result = db_service.delete_history("nonexistent_id")
        assert result is False

    def test_list_history_by_type(self, db_service):
        """测试按类型列出历史记录"""
        # 创建不同类型的记录
        for i in range(3):
            db_service.save_history(
                history_id=f"blog_{i}",
                topic=f"Blog {i}",
                article_type="tutorial",
                target_length="medium",
                markdown_content=f"# Blog {i}",
                outline='{}'
            )

        # 列出所有记录
        records = db_service.list_history_by_type(content_type=None, limit=10)
        assert len(records) >= 3

        # 按类型筛选 (blog 是默认类型)
        records = db_service.list_history_by_type(content_type='blog', limit=10)
        assert len(records) >= 3


# ========== 知识分块操作测试 ==========

@pytest.mark.unit
class TestChunkOperations:
    """知识分块操作测试"""

    def test_save_chunks(self, db_service, sample_doc_id):
        """测试保存知识分块"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 保存分块
        chunks = [
            {
                'chunk_type': 'text',
                'title': 'Introduction',
                'content': 'This is the introduction.',
                'start_pos': 0,
                'end_pos': 100
            },
            {
                'chunk_type': 'code',
                'title': 'Code Example',
                'content': 'print("Hello")',
                'start_pos': 100,
                'end_pos': 200
            }
        ]
        db_service.save_chunks(sample_doc_id, chunks)

        # 获取分块
        saved_chunks = db_service.get_chunks_by_document(sample_doc_id)
        assert len(saved_chunks) == 2
        assert saved_chunks[0]['title'] == 'Introduction'
        assert saved_chunks[1]['chunk_type'] == 'code'

    def test_get_chunks_by_documents(self, db_service):
        """测试批量获取文档分块"""
        # 创建多个文档并保存分块
        doc_ids = []
        for i in range(2):
            doc_id = f"doc_{i}"
            doc_ids.append(doc_id)
            db_service.create_document(
                doc_id=doc_id,
                filename=f"test_{i}.pdf",
                file_path=f"/tmp/test_{i}.pdf",
                file_size=1024,
                file_type="pdf"
            )
            db_service.save_chunks(doc_id, [
                {'chunk_type': 'text', 'title': f'Chunk {i}', 'content': f'Content {i}'}
            ])

        # 批量获取
        chunks = db_service.get_chunks_by_documents(doc_ids)
        assert len(chunks) == 2

        # 空列表
        chunks = db_service.get_chunks_by_documents([])
        assert len(chunks) == 0


# ========== 文档图片操作测试 ==========

@pytest.mark.unit
class TestImageOperations:
    """文档图片操作测试"""

    def test_save_images(self, db_service, sample_doc_id):
        """测试保存文档图片"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 保存图片
        images = [
            {
                'image_path': '/tmp/img1.jpg',
                'caption': 'Image 1',
                'page_num': 1
            },
            {
                'image_path': '/tmp/img2.jpg',
                'caption': 'Image 2',
                'page_num': 2
            }
        ]
        db_service.save_images(sample_doc_id, images)

        # 获取图片
        saved_images = db_service.get_images_by_document(sample_doc_id)
        assert len(saved_images) == 2
        assert saved_images[0]['caption'] == 'Image 1'
        assert saved_images[1]['page_num'] == 2

    def test_save_images_replaces_old(self, db_service, sample_doc_id):
        """测试保存图片会替换旧图片"""
        # 创建文档
        db_service.create_document(
            doc_id=sample_doc_id,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_type="pdf"
        )

        # 第一次保存
        db_service.save_images(sample_doc_id, [
            {'image_path': '/tmp/img1.jpg', 'caption': 'Old Image'}
        ])

        # 第二次保存（应该替换）
        db_service.save_images(sample_doc_id, [
            {'image_path': '/tmp/img2.jpg', 'caption': 'New Image'}
        ])

        # 验证只有新图片
        images = db_service.get_images_by_document(sample_doc_id)
        assert len(images) == 1
        assert images[0]['caption'] == 'New Image'
