"""
TDD 测试：特性 B — 自定义状态 Reducer
基于 102.10.1 细化实现方案 + Phase 4.5 修正。
"""
import pytest


class TestMergeListDedup:
    """merge_list_dedup 去重合并测试"""

    def test_both_empty(self):
        from services.blog_generator.schemas.reducers import merge_list_dedup
        assert merge_list_dedup([], []) == []

    def test_existing_none(self):
        from services.blog_generator.schemas.reducers import merge_list_dedup
        assert merge_list_dedup([], ["a", "b"]) == ["a", "b"]

    def test_new_none(self):
        from services.blog_generator.schemas.reducers import merge_list_dedup
        assert merge_list_dedup(["a", "b"], []) == ["a", "b"]

    def test_dedup_preserves_order(self):
        from services.blog_generator.schemas.reducers import merge_list_dedup
        result = merge_list_dedup(["a", "b", "c"], ["b", "c", "d"])
        assert result == ["a", "b", "c", "d"]

    def test_dedup_dict_items(self):
        """字典项按 str() 去重"""
        from services.blog_generator.schemas.reducers import merge_list_dedup
        existing = [{"url": "http://a.com", "title": "A"}]
        new = [{"url": "http://a.com", "title": "A"}, {"url": "http://b.com", "title": "B"}]
        result = merge_list_dedup(existing, new)
        assert len(result) == 2


class TestMergeSections:
    """merge_sections 按 id 合并测试"""

    def test_both_empty(self):
        from services.blog_generator.schemas.reducers import merge_sections
        assert merge_sections([], []) == []

    def test_new_section_added(self):
        from services.blog_generator.schemas.reducers import merge_sections
        existing = [{"id": "s1", "title": "A", "content": "old"}]
        new = [{"id": "s2", "title": "B", "content": "new"}]
        result = merge_sections(existing, new)
        assert len(result) == 2

    def test_same_id_overwritten(self):
        from services.blog_generator.schemas.reducers import merge_sections
        existing = [{"id": "s1", "title": "A", "content": "old"}]
        new = [{"id": "s1", "title": "A", "content": "updated"}]
        result = merge_sections(existing, new)
        assert len(result) == 1
        assert result[0]["content"] == "updated"

    def test_mixed_add_and_update(self):
        from services.blog_generator.schemas.reducers import merge_sections
        existing = [
            {"id": "s1", "content": "v1"},
            {"id": "s2", "content": "v1"},
        ]
        new = [
            {"id": "s2", "content": "v2"},  # 更新
            {"id": "s3", "content": "v1"},  # 新增
        ]
        result = merge_sections(existing, new)
        assert len(result) == 3
        s2 = next(s for s in result if s["id"] == "s2")
        assert s2["content"] == "v2"


class TestStateReducersRegistry:
    """STATE_REDUCERS 注册表测试"""

    def test_registry_has_search_results(self):
        from services.blog_generator.schemas.reducers import STATE_REDUCERS
        assert "search_results" in STATE_REDUCERS

    def test_registry_has_sections(self):
        from services.blog_generator.schemas.reducers import STATE_REDUCERS
        assert "sections" in STATE_REDUCERS

    def test_registry_values_are_callable(self):
        from services.blog_generator.schemas.reducers import STATE_REDUCERS
        for field, reducer in STATE_REDUCERS.items():
            assert callable(reducer), f"Reducer for {field} is not callable"

    def test_unregistered_field_not_in_registry(self):
        """未注册字段不在注册表中（使用默认覆盖行为）"""
        from services.blog_generator.schemas.reducers import STATE_REDUCERS
        assert "topic" not in STATE_REDUCERS
        assert "final_markdown" not in STATE_REDUCERS
