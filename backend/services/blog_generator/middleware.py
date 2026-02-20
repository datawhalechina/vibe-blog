"""
节点级中间件管道引擎（102.10 迁移特性 A）

将 DeerFlow 的 AgentMiddleware 思想适配到 VibeBlog 的 LangGraph DAG 架构。
每个中间件实现 before_node / after_node 钩子，通过 MiddlewarePipeline.wrap_node()
透明包装现有节点函数。

环境变量开关：MIDDLEWARE_PIPELINE_ENABLED (default: true)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ==================== 特性 A：NodeMiddleware 协议 + MiddlewarePipeline ====================


@runtime_checkable
class NodeMiddleware(Protocol):
    """节点中间件协议 — 所有中间件必须实现 before_node 和 after_node"""

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        """节点执行前调用。返回 dict 则合并到 state，返回 None 则不修改。"""
        ...

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        """节点执行后调用。返回 dict 则合并到 state，返回 None 则不修改。"""
        ...


class MiddlewarePipeline:
    """
    中间件管道 — 管理中间件注册和节点包装。

    用法：
        pipeline = MiddlewarePipeline(middlewares=[TracingMiddleware(), ...])
        wrapped_fn = pipeline.wrap_node("researcher", original_fn)
    """

    def __init__(self, middlewares: Optional[List[Any]] = None):
        self.middlewares: List[Any] = middlewares or []

    def wrap_node(
        self, node_name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """包装节点函数，注入 before/after 中间件钩子。"""
        middlewares = self.middlewares

        def wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
            # 功能开关检查
            if os.getenv("MIDDLEWARE_PIPELINE_ENABLED", "true").lower() == "false":
                return fn(state)

            current_state = dict(state)

            # before 阶段：按注册顺序执行
            for mw in middlewares:
                try:
                    patch = mw.before_node(current_state, node_name)
                    if patch and isinstance(patch, dict):
                        current_state.update(patch)
                except Exception:
                    logger.exception("Middleware %s.before_node failed for %s", type(mw).__name__, node_name)

            # 执行原始节点
            result = fn(current_state)

            # after 阶段：按注册顺序执行
            for mw in middlewares:
                try:
                    patch = mw.after_node(result, node_name)
                    if patch and isinstance(patch, dict):
                        result.update(patch)
                except Exception:
                    logger.exception("Middleware %s.after_node failed for %s", type(mw).__name__, node_name)

            return result

        return wrapped


# ==================== 特性 E：TracingMiddleware ====================


class TracingMiddleware:
    """
    分布式追踪中间件 — 复用现有 task_id_context ContextVar。

    在 before_node 中将 state["trace_id"] 写入 ContextVar，
    使后续日志自动带上 trace_id 前缀。

    环境变量开关：TRACING_ENABLED (default: true)
    """

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if os.getenv("TRACING_ENABLED", "true").lower() == "false":
            return None
        trace_id = state.get("trace_id")
        if trace_id:
            from logging_config import task_id_context
            task_id_context.set(trace_id)
        return None

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        return None


# ==================== 特性 C：ErrorTrackingMiddleware ====================


class ErrorTrackingMiddleware:
    """
    错误追踪中间件 — 收集节点产生的 _node_errors 到 error_history。

    节点通过在返回 state 中设置 _node_errors: List[dict] 来报告错误，
    本中间件在 after_node 中将其转移到 error_history 并清空 _node_errors。
    """

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        return None

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        node_errors = state.get("_node_errors", [])
        if not node_errors:
            return None
        error_history = list(state.get("error_history", []))
        error_history.extend(node_errors)
        return {"error_history": error_history, "_node_errors": []}


# ==================== 特性 H：TokenBudgetMiddleware ====================


class TokenBudgetMiddleware:
    """
    主动式 Token 预算管理中间件 — 包装现有 ContextCompressor。

    在 before_node 中分配节点预算，预算不足时主动触发压缩。
    在 after_node 中记录实际 token 消耗。

    环境变量开关：TOKEN_BUDGET_ENABLED (default: true)
    """

    NODE_BUDGET_WEIGHTS = {
        "researcher": 0.10,
        "planner": 0.10,
        "writer": 0.35,
        "reviewer": 0.10,
        "revision": 0.15,
        "coder_and_artist": 0.10,
        "assembler": 0.05,
    }
    DEFAULT_WEIGHT = 0.05

    def __init__(self, compressor=None, token_tracker=None, total_budget: int = 500000):
        self.compressor = compressor
        self.token_tracker = token_tracker
        self.total_budget = total_budget
        self._used_tokens = 0

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if os.getenv("TOKEN_BUDGET_ENABLED", "true").lower() == "false":
            return None

        weight = self.NODE_BUDGET_WEIGHTS.get(node_name, self.DEFAULT_WEIGHT)
        node_budget = int(self.total_budget * weight)
        result: Dict[str, Any] = {"_node_budget": node_budget}

        # 预算使用超过 80% 时触发压缩
        if self._used_tokens > self.total_budget * 0.8 and self.compressor:
            messages = state.get("_messages", [])
            if messages:
                self.compressor.apply_strategy(messages)
                result["_budget_warning"] = True

        return result

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if self.token_tracker and hasattr(self.token_tracker, "last_call"):
            last_call = self.token_tracker.last_call
            if last_call and hasattr(last_call, "total_tokens"):
                self._used_tokens += last_call.total_tokens
        return None


# ==================== 特性 G：ContextPrefetchMiddleware ====================


class ContextPrefetchMiddleware:
    """
    上下文预取中间件 — 在首个节点（researcher）前并行预取知识库文档。

    仅在 researcher 节点且首次调用时触发预取。

    环境变量开关：CONTEXT_PREFETCH_ENABLED (default: true)
    """

    def __init__(self, knowledge_service=None, timeout: float = 30.0):
        self.knowledge_service = knowledge_service
        self.timeout = timeout
        self._prefetched = False

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if os.getenv("CONTEXT_PREFETCH_ENABLED", "true").lower() == "false":
            return None

        # 仅在 researcher 节点触发
        if node_name != "researcher":
            return None

        # 仅首次调用
        if self._prefetched:
            return None
        self._prefetched = True

        doc_ids = state.get("document_ids", [])
        if not doc_ids or not self.knowledge_service:
            return None

        # 带超时的预取
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.knowledge_service.batch_load, doc_ids)
                docs = future.result(timeout=self.timeout)
                if docs:
                    return {"prefetch_docs": docs}
        except (FuturesTimeout, Exception):
            logger.warning("Context prefetch timed out or failed for %s", doc_ids)

        return None

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        return None


# ==================== 特性 B：ReducerMiddleware ====================


class ReducerMiddleware:
    """
    状态合并中间件 — 在 after_node 中用 STATE_REDUCERS 合并列表字段。

    解决并行节点写入同一字段时后写覆盖前写的问题。
    对于注册了 reducer 的字段，用 reducer 函数合并而非直接覆盖。

    环境变量开关：STATE_REDUCERS_ENABLED (default: true)
    """

    def __init__(self):
        from .schemas.reducers import STATE_REDUCERS
        self._reducers = STATE_REDUCERS
        self._snapshot: Dict[str, list] = {}

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        # 记录 before 快照，供 after 阶段做 diff
        self._snapshot = {
            field: list(state.get(field, []))
            for field in self._reducers
            if field in state
        }
        return None

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if os.getenv("STATE_REDUCERS_ENABLED", "true").lower() == "false":
            return None

        patch: Dict[str, Any] = {}
        for field, reducer in self._reducers.items():
            if field not in state:
                continue
            old_val = self._snapshot.get(field, [])
            new_val = state.get(field, [])
            # 只在值发生变化时才合并
            if new_val is not old_val and new_val != old_val:
                patch[field] = reducer(old_val, new_val)

        return patch if patch else None
