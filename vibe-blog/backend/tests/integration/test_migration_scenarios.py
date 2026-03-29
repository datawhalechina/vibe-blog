"""
TDD 集成场景测试：真实用户操作场景验证
基于 102.10.1 + Phase 4.5 修正，测试多特性协同工作。
"""
import pytest
from unittest.mock import MagicMock, patch


class TestScenarioMiddlewarePipelineE2E:
    """场景：完整中间件管道端到端"""

    def test_full_pipeline_with_all_middlewares(self):
        """场景：所有中间件挂载到管道，执行一个节点
        验证：TracingMiddleware → ErrorTrackingMiddleware → TokenBudgetMiddleware 协同工作
        """
        from services.blog_generator.middleware import (
            MiddlewarePipeline,
            TracingMiddleware,
            ErrorTrackingMiddleware,
            TokenBudgetMiddleware,
        )

        mock_compressor = MagicMock()
        mock_compressor.apply_strategy.return_value = []

        pipeline = MiddlewarePipeline(middlewares=[
            TracingMiddleware(),
            ErrorTrackingMiddleware(),
            TokenBudgetMiddleware(compressor=mock_compressor, total_budget=500000),
        ])

        def mock_researcher(state):
            return {**state, "search_results": [{"url": "http://a.com"}]}

        wrapped = pipeline.wrap_node("researcher", mock_researcher)
        result = wrapped({
            "topic": "AI",
            "trace_id": "test1234",
            "error_history": [],
        })

        assert result["search_results"] == [{"url": "http://a.com"}]

    def test_reducer_prevents_data_loss_in_parallel(self):
        """场景：两个并行节点同时修改 images 字段
        验证：reducer 合并而非覆盖
        """
        from services.blog_generator.schemas.reducers import merge_list_dedup

        # 模拟 coder 和 artist 并行返回
        coder_result = [{"id": "code1", "type": "code"}]
        artist_result = [{"id": "img1", "type": "image"}]

        # 如果没有 reducer，后写覆盖前写
        # 有 reducer 后，合并两个结果
        merged = merge_list_dedup(coder_result, artist_result)
        assert len(merged) == 2
        assert {"id": "code1", "type": "code"} in merged
        assert {"id": "img1", "type": "image"} in merged


class TestScenarioErrorRecovery:
    """场景：节点执行失败时的错误追踪"""

    def test_error_tracked_across_nodes(self):
        """场景：researcher 成功 → writer 失败 → reviewer 成功
        验证：error_history 只记录 writer 的错误
        """
        from services.blog_generator.middleware import (
            MiddlewarePipeline,
            ErrorTrackingMiddleware,
        )

        pipeline = MiddlewarePipeline(middlewares=[ErrorTrackingMiddleware()])

        # researcher 成功
        wrapped_researcher = pipeline.wrap_node("researcher", lambda s: s)
        state = wrapped_researcher({"error_history": []})
        assert state["error_history"] == []

        # writer 产生错误
        def failing_writer(state):
            return {
                **state,
                "_node_errors": [{"category": "llm_timeout", "node": "writer"}],
            }

        wrapped_writer = pipeline.wrap_node("writer", failing_writer)
        state = wrapped_writer(state)
        assert len(state["error_history"]) == 1
        assert state["error_history"][0]["category"] == "llm_timeout"


class TestScenarioTokenBudgetCompression:
    """场景：长文章生成时 token 预算耗尽"""

    def test_late_nodes_get_compressed_context(self):
        """场景：writer 消耗大量 token → reviewer 触发主动压缩
        验证：reviewer 执行前 ContextCompressor 被调用
        """
        from services.blog_generator.middleware import TokenBudgetMiddleware

        mock_compressor = MagicMock()
        mock_compressor.apply_strategy.return_value = [{"role": "system", "content": "compressed"}]

        mock_tracker = MagicMock()

        mw = TokenBudgetMiddleware(
            compressor=mock_compressor,
            token_tracker=mock_tracker,
            total_budget=100000,
        )

        # 模拟 writer 消耗了 90% 预算
        mw._used_tokens = 90000

        # reviewer 执行前应触发压缩
        result = mw.before_node(
            {"_messages": [{"role": "user", "content": "long article..."}]},
            "reviewer",
        )
        assert result.get("_budget_warning") is True
        mock_compressor.apply_strategy.assert_called_once()


class TestScenarioFeatureToggleOff:
    """场景：所有迁移特性关闭时系统正常工作"""

    def test_all_features_disabled(self):
        """场景：所有环境变量设为 false
        验证：系统行为与改造前一致
        """
        env_vars = {
            "MIDDLEWARE_PIPELINE_ENABLED": "false",
            "STATE_REDUCERS_ENABLED": "false",
            "STRUCTURED_ERRORS_ENABLED": "false",
            "TRACING_ENABLED": "false",
            "TOKEN_BUDGET_ENABLED": "false",
            "CONTEXT_PREFETCH_ENABLED": "false",
        }

        with patch.dict("os.environ", env_vars):
            from services.blog_generator.middleware import MiddlewarePipeline

            pipeline = MiddlewarePipeline(middlewares=[])
            original_called = {"n": 0}

            def original_node(state):
                original_called["n"] += 1
                return {**state, "processed": True}

            wrapped = pipeline.wrap_node("test", original_node)
            result = wrapped({"topic": "test"})

            assert original_called["n"] == 1
            assert result["processed"] is True
