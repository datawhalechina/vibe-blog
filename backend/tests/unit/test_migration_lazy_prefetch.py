"""
TDD 测试：特性 F — 懒初始化 + 特性 G — 上下文预取
基于 102.10.1 细化实现方案。
"""
import pytest
import threading
from unittest.mock import MagicMock, patch


# ==================== 特性 F：LazyResource ====================

class TestLazyResource:
    """LazyResource 描述符测试"""

    def test_first_access_creates(self):
        """首次访问时调用 factory 创建"""
        from utils.lazy import LazyResource

        create_count = {"n": 0}

        class Service:
            resource = LazyResource(factory=lambda self: self._create())
            def _create(self):
                create_count["n"] += 1
                return "created"

        svc = Service()
        assert svc.resource == "created"
        assert create_count["n"] == 1

    def test_second_access_cached(self):
        """二次访问返回缓存值"""
        from utils.lazy import LazyResource

        create_count = {"n": 0}

        class Service:
            resource = LazyResource(factory=lambda self: self._create())
            def _create(self):
                create_count["n"] += 1
                return "created"

        svc = Service()
        _ = svc.resource
        _ = svc.resource
        assert create_count["n"] == 1

    def test_reset_clears_cache(self):
        """reset() 清理缓存，下次访问重新创建"""
        from utils.lazy import LazyResource

        create_count = {"n": 0}

        class Service:
            resource = LazyResource(factory=lambda self: self._create())
            def _create(self):
                create_count["n"] += 1
                return f"v{create_count['n']}"

        svc = Service()
        assert svc.resource == "v1"
        type(svc).resource.reset(svc)
        assert svc.resource == "v2"
        assert create_count["n"] == 2

    def test_cleanup_called_on_reset(self):
        """reset() 时调用 cleanup 回调"""
        from utils.lazy import LazyResource

        cleaned = []

        class Service:
            resource = LazyResource(
                factory=lambda self: "value",
                cleanup=lambda val: cleaned.append(val),
            )

        svc = Service()
        _ = svc.resource
        type(svc).resource.reset(svc)
        assert cleaned == ["value"]

    def test_thread_safety(self):
        """并发访问不重复创建"""
        from utils.lazy import LazyResource
        import time

        create_count = {"n": 0}

        class Service:
            resource = LazyResource(factory=lambda self: self._slow_create())
            def _slow_create(self):
                create_count["n"] += 1
                time.sleep(0.01)
                return "created"

        svc = Service()
        results = []

        def access():
            results.append(svc.resource)

        threads = [threading.Thread(target=access) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert create_count["n"] == 1
        assert all(r == "created" for r in results)

    def test_different_instances_independent(self):
        """不同实例的 LazyResource 独立"""
        from utils.lazy import LazyResource

        class Service:
            resource = LazyResource(factory=lambda self: id(self))

        svc1 = Service()
        svc2 = Service()
        assert svc1.resource != svc2.resource

    def test_class_access_returns_descriptor(self):
        """通过类访问返回描述符本身"""
        from utils.lazy import LazyResource

        class Service:
            resource = LazyResource(factory=lambda self: "value")

        assert isinstance(Service.resource, LazyResource)


# ==================== 特性 G：ContextPrefetchMiddleware ====================

class TestContextPrefetchMiddleware:
    """上下文预取中间件测试"""

    def test_prefetch_on_first_node(self):
        """仅在首个节点（researcher）前预取"""
        from services.blog_generator.middleware import ContextPrefetchMiddleware

        mock_ks = MagicMock()
        mock_ks.batch_load.return_value = [{"id": "d1", "content": "doc1"}]

        mw = ContextPrefetchMiddleware(knowledge_service=mock_ks)
        state = {"document_ids": ["d1"], "topic": "test"}

        result = mw.before_node(state, "researcher")
        assert result is not None
        assert "prefetch_docs" in result
        mock_ks.batch_load.assert_called_once_with(["d1"])

    def test_no_prefetch_on_second_call(self):
        """第二次调用不再预取"""
        from services.blog_generator.middleware import ContextPrefetchMiddleware

        mock_ks = MagicMock()
        mock_ks.batch_load.return_value = []

        mw = ContextPrefetchMiddleware(knowledge_service=mock_ks)
        state = {"document_ids": ["d1"]}

        mw.before_node(state, "researcher")
        result = mw.before_node(state, "planner")
        assert result is None

    def test_no_prefetch_without_docs(self):
        """无文档 ID 时不预取"""
        from services.blog_generator.middleware import ContextPrefetchMiddleware

        mock_ks = MagicMock()
        mw = ContextPrefetchMiddleware(knowledge_service=mock_ks)
        state = {"document_ids": [], "topic": "test"}

        result = mw.before_node(state, "researcher")
        # 无文档时返回 None 或空
        mock_ks.batch_load.assert_not_called()

    def test_prefetch_timeout_no_block(self):
        """预取超时不阻塞主流程"""
        from services.blog_generator.middleware import ContextPrefetchMiddleware
        import time

        mock_ks = MagicMock()
        def slow_load(ids):
            time.sleep(60)  # 模拟超时
            return []
        mock_ks.batch_load.side_effect = slow_load

        mw = ContextPrefetchMiddleware(knowledge_service=mock_ks)
        state = {"document_ids": ["d1"]}

        # 应在 30s 超时后返回，不阻塞
        # 注意：实际测试中不会等 60s，因为 ThreadPoolExecutor 有 timeout
        result = mw.before_node(state, "researcher")
        # 超时后 prefetch_docs 不在结果中
        assert result is None or "prefetch_docs" not in (result or {})

    def test_skip_non_researcher_node(self):
        """非 researcher 节点跳过预取"""
        from services.blog_generator.middleware import ContextPrefetchMiddleware

        mock_ks = MagicMock()
        mw = ContextPrefetchMiddleware(knowledge_service=mock_ks)
        state = {"document_ids": ["d1"]}

        result = mw.before_node(state, "writer")
        assert result is None
        mock_ks.batch_load.assert_not_called()

    def test_disabled_via_env(self):
        """CONTEXT_PREFETCH_ENABLED=false 时跳过"""
        from services.blog_generator.middleware import ContextPrefetchMiddleware

        mock_ks = MagicMock()
        with patch.dict("os.environ", {"CONTEXT_PREFETCH_ENABLED": "false"}):
            mw = ContextPrefetchMiddleware(knowledge_service=mock_ks)
            state = {"document_ids": ["d1"]}
            result = mw.before_node(state, "researcher")
            mock_ks.batch_load.assert_not_called()
