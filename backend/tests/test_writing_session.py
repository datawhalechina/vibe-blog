"""
WritingSession + WritingSessionManager 单元测试
TDD: 先写测试，再写实现
测试用例 WS1-WS11
"""
import pytest
from services.chat.writing_session import WritingSession, WritingSessionManager


class TestWritingSessionCreate:
    """WS1-WS2: 创建会话"""

    def test_ws1_session_id_prefix(self, session_mgr):
        """WS1: session_id 以 ws_ 开头"""
        session = session_mgr.create(topic="测试主题")
        assert session.session_id.startswith("ws_")
        assert len(session.session_id) > 10

    def test_ws2_default_fields(self, session_mgr):
        """WS2: 默认字段值正确"""
        session = session_mgr.create(topic="AI 入门")
        assert session.topic == "AI 入门"
        assert session.article_type == "problem-solution"
        assert session.target_audience == "beginner"
        assert session.target_length == "medium"
        assert session.outline is None
        assert session.sections == []
        assert session.search_results == []
        assert session.status == "created"
        assert session.created_at is not None
        assert session.updated_at is not None


class TestWritingSessionGet:
    """WS3-WS4: 获取会话"""

    def test_ws3_get_existing(self, session_mgr):
        """WS3: 获取存在的会话"""
        created = session_mgr.create(topic="测试")
        fetched = session_mgr.get(created.session_id)
        assert fetched is not None
        assert fetched.session_id == created.session_id
        assert fetched.topic == "测试"

    def test_ws4_get_nonexistent(self, session_mgr):
        """WS4: 获取不存在的会话返回 None"""
        result = session_mgr.get("ws_nonexistent_id")
        assert result is None


class TestWritingSessionUpdate:
    """WS5-WS8: 更新会话"""

    def test_ws5_update_topic(self, session_mgr):
        """WS5: 更新 topic"""
        session = session_mgr.create(topic="旧主题")
        updated = session_mgr.update(session.session_id, topic="新主题")
        assert updated.topic == "新主题"
        # 重新获取确认持久化
        fetched = session_mgr.get(session.session_id)
        assert fetched.topic == "新主题"

    def test_ws6_update_outline_json(self, session_mgr):
        """WS6: 更新 outline (JSON 字段)"""
        session = session_mgr.create(topic="测试")
        outline = {"title": "AI 指南", "sections": [{"id": "s1", "title": "简介"}]}
        updated = session_mgr.update(session.session_id, outline=outline)
        assert updated.outline == outline
        # 重新获取确认 JSON 序列化/反序列化
        fetched = session_mgr.get(session.session_id)
        assert fetched.outline == outline

    def test_ws7_update_sections_list(self, session_mgr):
        """WS7: 更新 sections (JSON 列表)"""
        session = session_mgr.create(topic="测试")
        sections = [
            {"id": "s1", "title": "简介", "content": "这是简介"},
            {"id": "s2", "title": "正文", "content": "这是正文"},
        ]
        updated = session_mgr.update(session.session_id, sections=sections)
        assert updated.sections == sections
        assert len(updated.sections) == 2

    def test_ws8_updated_at_auto_update(self, session_mgr):
        """WS8: updated_at 自动更新"""
        import time
        session = session_mgr.create(topic="测试")
        old_updated = session.updated_at
        time.sleep(0.01)  # 确保时间差
        updated = session_mgr.update(session.session_id, topic="新主题")
        assert updated.updated_at >= old_updated


class TestWritingSessionList:
    """WS9: 列出会话"""

    def test_ws9_list_with_pagination(self, session_mgr):
        """WS9: limit/offset 分页"""
        for i in range(5):
            session_mgr.create(topic=f"主题 {i}")
        # 全部
        all_sessions = session_mgr.list(limit=10)
        assert len(all_sessions) == 5
        # 分页
        page1 = session_mgr.list(limit=2, offset=0)
        assert len(page1) == 2
        page2 = session_mgr.list(limit=2, offset=2)
        assert len(page2) == 2
        page3 = session_mgr.list(limit=2, offset=4)
        assert len(page3) == 1


class TestWritingSessionDelete:
    """WS10-WS11: 删除会话"""

    def test_ws10_delete_existing(self, session_mgr):
        """WS10: 成功删除"""
        session = session_mgr.create(topic="待删除")
        result = session_mgr.delete(session.session_id)
        assert result is True
        assert session_mgr.get(session.session_id) is None

    def test_ws11_delete_nonexistent(self, session_mgr):
        """WS11: 不存在返回 False"""
        result = session_mgr.delete("ws_nonexistent")
        assert result is False


class TestWritingSessionUserIsolation:
    """WS12-WS16: user_id 用户隔离"""

    def test_ws12_create_with_user_id(self, session_mgr):
        """WS12: 创建会话时指定 user_id"""
        session = session_mgr.create(topic="用户A的主题", user_id="user_a")
        assert session.user_id == "user_a"
        fetched = session_mgr.get(session.session_id)
        assert fetched.user_id == "user_a"

    def test_ws13_get_filtered_by_user_id(self, session_mgr):
        """WS13: 按 user_id 过滤获取会话"""
        s_a = session_mgr.create(topic="A的会话", user_id="user_a")
        s_b = session_mgr.create(topic="B的会话", user_id="user_b")
        # user_a 只能看到自己的
        assert session_mgr.get(s_a.session_id, user_id="user_a") is not None
        assert session_mgr.get(s_b.session_id, user_id="user_a") is None
        # user_b 只能看到自己的
        assert session_mgr.get(s_b.session_id, user_id="user_b") is not None
        assert session_mgr.get(s_a.session_id, user_id="user_b") is None

    def test_ws14_get_without_user_id_returns_all(self, session_mgr):
        """WS14: 不传 user_id 时可获取任意会话（管理员模式）"""
        s_a = session_mgr.create(topic="A的会话", user_id="user_a")
        fetched = session_mgr.get(s_a.session_id)
        assert fetched is not None
        assert fetched.user_id == "user_a"

    def test_ws15_list_filtered_by_user_id(self, session_mgr):
        """WS15: 按 user_id 过滤列表"""
        for i in range(3):
            session_mgr.create(topic=f"A-{i}", user_id="user_a")
        for i in range(2):
            session_mgr.create(topic=f"B-{i}", user_id="user_b")
        assert len(session_mgr.list(user_id="user_a")) == 3
        assert len(session_mgr.list(user_id="user_b")) == 2
        assert len(session_mgr.list()) == 5  # 不传 user_id 返回全部

    def test_ws16_default_user_id_empty(self, session_mgr):
        """WS16: 不传 user_id 时默认为空字符串"""
        session = session_mgr.create(topic="无用户")
        assert session.user_id == ""


# ============ Fixtures ============

@pytest.fixture
def session_mgr():
    """In-memory WritingSessionManager for testing."""
    return WritingSessionManager(db_path=":memory:")
