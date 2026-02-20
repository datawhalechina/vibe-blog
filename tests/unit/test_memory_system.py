"""
102.03 持久化记忆系统 — 单元测试
覆盖：MemoryStorage CRUD、mtime 缓存、原子写入、事实管理、
      profile 更新、注入格式化、BlogMemoryConfig、边界条件
"""

import json
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from services.blog_generator.memory.storage import MemoryStorage, create_empty_memory
from services.blog_generator.memory.config import BlogMemoryConfig


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def storage(tmp_path):
    return MemoryStorage(storage_path=str(tmp_path))


@pytest.fixture
def user_id():
    return "test_user_001"


# ============================================================
# 1. 空记忆结构
# ============================================================

class TestEmptyMemory:
    def test_create_empty_has_all_sections(self):
        m = create_empty_memory("u1")
        assert m["version"] == "1.0"
        assert m["userId"] == "u1"
        assert "writingProfile" in m
        assert "topicHistory" in m
        assert "qualityPreferences" in m
        assert m["facts"] == []

    def test_writing_profile_fields(self):
        m = create_empty_memory("u1")
        wp = m["writingProfile"]
        for key in ["preferredStyle", "preferredLength", "preferredAudience", "preferredImageStyle"]:
            assert key in wp
            assert wp[key]["summary"] == ""


# ============================================================
# 2. MemoryStorage 基本 CRUD
# ============================================================

class TestStorageCRUD:
    def test_load_creates_empty_for_new_user(self, storage, user_id):
        m = storage.load(user_id)
        assert m["userId"] == user_id
        assert m["facts"] == []

    def test_save_and_load(self, storage, user_id):
        m = storage.load(user_id)
        m["writingProfile"]["preferredStyle"]["summary"] = "深入浅出"
        assert storage.save(user_id, m) is True

        loaded = storage.load(user_id)
        assert loaded["writingProfile"]["preferredStyle"]["summary"] == "深入浅出"

    def test_save_updates_last_updated(self, storage, user_id):
        m = storage.load(user_id)
        storage.save(user_id, m)
        loaded = storage.load(user_id)
        assert loaded["lastUpdated"] != ""

    def test_exists(self, storage, user_id):
        assert storage.exists(user_id) is False
        storage.save(user_id, create_empty_memory(user_id))
        assert storage.exists(user_id) is True

    def test_delete(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        assert storage.exists(user_id) is True
        assert storage.delete(user_id) is True
        assert storage.exists(user_id) is False

    def test_delete_nonexistent(self, storage):
        assert storage.delete("nonexistent") is False


# ============================================================
# 3. mtime 缓存
# ============================================================

class TestMtimeCache:
    def test_cache_hit(self, storage, user_id):
        m = create_empty_memory(user_id)
        m["writingProfile"]["preferredStyle"]["summary"] = "cached"
        storage.save(user_id, m)

        # 第二次 load 应命中缓存
        loaded = storage.load(user_id)
        assert loaded["writingProfile"]["preferredStyle"]["summary"] == "cached"

    def test_cache_invalidated_on_external_change(self, storage, user_id, tmp_path):
        m = create_empty_memory(user_id)
        storage.save(user_id, m)
        storage.load(user_id)  # 填充缓存

        # 外部修改文件
        time.sleep(0.05)
        file_path = tmp_path / f"{user_id}.json"
        data = json.loads(file_path.read_text())
        data["writingProfile"]["preferredStyle"]["summary"] = "外部修改"
        file_path.write_text(json.dumps(data, ensure_ascii=False))

        loaded = storage.load(user_id)
        assert loaded["writingProfile"]["preferredStyle"]["summary"] == "外部修改"


# ============================================================
# 4. 原子写入
# ============================================================

class TestAtomicWrite:
    def test_no_tmp_file_left(self, storage, user_id, tmp_path):
        storage.save(user_id, create_empty_memory(user_id))
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_file_is_valid_json(self, storage, user_id, tmp_path):
        storage.save(user_id, create_empty_memory(user_id))
        file_path = tmp_path / f"{user_id}.json"
        data = json.loads(file_path.read_text())
        assert data["userId"] == user_id


# ============================================================
# 5. 事实管理
# ============================================================

class TestFactManagement:
    def test_add_fact(self, storage, user_id):
        fact_id = storage.add_fact(user_id, "偏好 Python 代码示例", category="preference")
        assert fact_id is not None
        assert fact_id.startswith("fact_")

        m = storage.load(user_id)
        assert len(m["facts"]) == 1
        assert m["facts"][0]["content"] == "偏好 Python 代码示例"
        assert m["facts"][0]["category"] == "preference"

    def test_remove_fact(self, storage, user_id):
        fact_id = storage.add_fact(user_id, "test fact")
        assert storage.remove_fact(user_id, fact_id) is True
        assert len(storage.load(user_id)["facts"]) == 0

    def test_remove_nonexistent_fact(self, storage, user_id):
        assert storage.remove_fact(user_id, "nonexistent") is False

    def test_get_facts_by_category(self, storage, user_id):
        storage.add_fact(user_id, "fact A", category="preference")
        storage.add_fact(user_id, "fact B", category="knowledge")
        storage.add_fact(user_id, "fact C", category="preference")

        prefs = storage.get_facts_by_category(user_id, "preference")
        assert len(prefs) == 2
        assert all(f["category"] == "preference" for f in prefs)

    def test_max_facts_limit(self, storage, user_id):
        for i in range(15):
            storage.add_fact(user_id, f"fact {i}", confidence=0.5 + i * 0.03, max_facts=10)
        m = storage.load(user_id)
        assert len(m["facts"]) <= 10

    def test_fact_with_source(self, storage, user_id):
        storage.add_fact(user_id, "test", source="task_abc123")
        m = storage.load(user_id)
        assert m["facts"][0]["source"] == "task_abc123"


# ============================================================
# 6. Profile 更新
# ============================================================

class TestProfileUpdate:
    def test_update_writing_profile(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        result = storage.update_profile_field(
            user_id, "writingProfile", "preferredStyle", "深入浅出的技术写作"
        )
        assert result is True
        m = storage.load(user_id)
        assert m["writingProfile"]["preferredStyle"]["summary"] == "深入浅出的技术写作"
        assert m["writingProfile"]["preferredStyle"]["updatedAt"] != ""

    def test_update_topic_history(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        result = storage.update_profile_field(
            user_id, "topicHistory", "recentTopics", "AI Agent, RAG, LangGraph"
        )
        assert result is True

    def test_update_invalid_section(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        assert storage.update_profile_field(user_id, "nonexistent", "field", "val") is False

    def test_update_invalid_field(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        assert storage.update_profile_field(user_id, "writingProfile", "nonexistent", "val") is False


# ============================================================
# 7. 注入格式化
# ============================================================

class TestInjectionFormatting:
    def test_empty_memory_returns_empty(self, storage, user_id):
        assert storage.format_for_injection(user_id) == ""

    def test_with_profile(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        storage.update_profile_field(user_id, "writingProfile", "preferredStyle", "深入浅出")
        result = storage.format_for_injection(user_id)
        assert "<user-memory>" in result
        assert "写作风格: 深入浅出" in result
        assert "</user-memory>" in result

    def test_with_facts(self, storage, user_id):
        storage.add_fact(user_id, "偏好 Python", category="preference", confidence=0.95)
        result = storage.format_for_injection(user_id)
        assert "[preference] 偏好 Python" in result

    def test_top_facts_limited(self, storage, user_id):
        for i in range(20):
            storage.add_fact(user_id, f"fact {i}", confidence=0.5 + i * 0.02)
        result = storage.format_for_injection(user_id)
        # 最多注入 10 条
        fact_lines = [l for l in result.split("\n") if l.startswith("- [")]
        assert len(fact_lines) <= 10

    def test_full_injection(self, storage, user_id):
        storage.save(user_id, create_empty_memory(user_id))
        storage.update_profile_field(user_id, "writingProfile", "preferredStyle", "深入浅出")
        storage.update_profile_field(user_id, "topicHistory", "recentTopics", "AI Agent")
        storage.add_fact(user_id, "偏好 Python", category="preference")
        result = storage.format_for_injection(user_id)
        assert "用户写作偏好" in result
        assert "主题历史" in result
        assert "关键事实" in result


# ============================================================
# 8. BlogMemoryConfig
# ============================================================

class TestBlogMemoryConfig:
    def test_defaults(self):
        config = BlogMemoryConfig()
        assert config.enabled is True
        assert config.storage_backend == "json"
        assert config.max_facts == 200
        assert config.fact_confidence_threshold == 0.7

    def test_from_env(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MEMORY_ENABLED", "false")
            mp.setenv("MEMORY_MAX_FACTS", "50")
            config = BlogMemoryConfig.from_env()
            assert config.enabled is False
            assert config.max_facts == 50


# ============================================================
# 9. 用户隔离
# ============================================================

class TestUserIsolation:
    def test_different_users_isolated(self, storage):
        storage.add_fact("user_a", "fact for A", category="preference")
        storage.add_fact("user_b", "fact for B", category="knowledge")

        facts_a = storage.get_facts_by_category("user_a", "preference")
        facts_b = storage.get_facts_by_category("user_b", "knowledge")

        assert len(facts_a) == 1 and facts_a[0]["content"] == "fact for A"
        assert len(facts_b) == 1 and facts_b[0]["content"] == "fact for B"

    def test_safe_user_id(self, storage):
        """路径遍历攻击防护"""
        storage.save("../evil", create_empty_memory("../evil"))
        # 文件名应被清理
        assert not (storage._base_path / ".." / "evil.json").exists()


# ============================================================
# 10. 损坏文件恢复
# ============================================================

class TestCorruptedFile:
    def test_corrupted_json_returns_empty(self, storage, user_id, tmp_path):
        file_path = tmp_path / f"{user_id}.json"
        file_path.write_text("{ invalid json !!!")
        m = storage.load(user_id)
        assert m["userId"] == user_id
        assert m["facts"] == []
