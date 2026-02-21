"""
节点级中间件管道引擎（102.10 迁移特性 A + 102.02 中间件管道升级）

将 DeerFlow 的 AgentMiddleware 思想适配到 VibeBlog 的 LangGraph DAG 架构。
每个中间件实现 before_node / after_node 钩子，通过 MiddlewarePipeline.wrap_node()
透明包装现有节点函数。

102.02 新增：
- before_pipeline / after_pipeline 全局钩子
- on_error 降级钩子
- FeatureToggleMiddleware 统一功能开关
- GracefulDegradationMiddleware 统一降级处理

环境变量开关：MIDDLEWARE_PIPELINE_ENABLED (default: true)
"""

from __future__ import annotations

import contextvars
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# 当前执行节点名称，供 LLMService 自动归因 token 使用
current_node_name: contextvars.ContextVar[str] = contextvars.ContextVar("current_node_name", default="")


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


class ExtendedMiddleware:
    """
    扩展中间件基类（102.02）— 支持全局钩子和错误处理。

    子类可选覆盖 before_pipeline / after_pipeline / on_error。
    同时满足 NodeMiddleware 协议。
    """

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        return None

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        return None

    def before_pipeline(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """流水线开始前。用于全局初始化。"""
        return None

    def after_pipeline(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """流水线结束后。用于全局清理和汇总。"""
        return None

    def on_error(self, state: Dict[str, Any], node_name: str, error: Exception) -> Optional[Dict[str, Any]]:
        """节点异常时。返回 dict 表示降级成功，返回 None 表示继续抛出。"""
        return None


class MiddlewarePipeline:
    """
    中间件管道 — 管理中间件注册和节点包装。

    102.02 增强：支持 before_pipeline / after_pipeline / on_error 钩子。

    用法：
        pipeline = MiddlewarePipeline(middlewares=[TracingMiddleware(), ...])
        state = pipeline.run_before_pipeline(state)
        wrapped_fn = pipeline.wrap_node("researcher", original_fn)
        state = pipeline.run_after_pipeline(state)
    """

    def __init__(self, middlewares: Optional[List[Any]] = None):
        self.middlewares: List[Any] = middlewares or []

    def run_before_pipeline(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行所有中间件的 before_pipeline 钩子（正序）"""
        for mw in self.middlewares:
            if hasattr(mw, "before_pipeline"):
                try:
                    patch = mw.before_pipeline(state)
                    if patch and isinstance(patch, dict):
                        state.update(patch)
                except Exception:
                    logger.exception("Middleware %s.before_pipeline failed", type(mw).__name__)
        return state

    def run_after_pipeline(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行所有中间件的 after_pipeline 钩子（逆序）"""
        for mw in reversed(self.middlewares):
            if hasattr(mw, "after_pipeline"):
                try:
                    patch = mw.after_pipeline(state)
                    if patch and isinstance(patch, dict):
                        state.update(patch)
                except Exception:
                    logger.exception("Middleware %s.after_pipeline failed", type(mw).__name__)
        return state

    def wrap_node(
        self, node_name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """包装节点函数，注入 before/after/on_error 中间件钩子。"""
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

            # 执行原始节点（带 on_error 降级）
            start_time = time.time()
            token = current_node_name.set(node_name)
            try:
                result = fn(current_state)
            except Exception as e:
                # on_error 阶段：第一个处理成功的中间件生效
                for mw in middlewares:
                    if hasattr(mw, "on_error"):
                        try:
                            recovery = mw.on_error(current_state, node_name, e)
                            if recovery is not None:
                                current_state.update(recovery)
                                result = current_state
                                logger.warning("[%s] 降级处理 %s: %s", type(mw).__name__, node_name, e)
                                break
                        except Exception:
                            logger.exception("Middleware %s.on_error failed for %s", type(mw).__name__, node_name)
                else:
                    raise  # 没有中间件处理，继续抛出
            finally:
                current_node_name.reset(token)

            duration_ms = int((time.time() - start_time) * 1000)
            if isinstance(result, dict):
                result["_last_duration_ms"] = duration_ms

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


# ==================== 102.02：FeatureToggleMiddleware ====================


# 功能开关映射表：节点名 → (环境变量, StyleProfile 属性)
TOGGLE_MAP: Dict[str, tuple] = {
    "humanizer": ("HUMANIZER_ENABLED", "enable_humanizer"),
    "factcheck": ("FACTCHECK_ENABLED", "enable_fact_check"),
    "text_cleanup": ("TEXT_CLEANUP_ENABLED", "enable_text_cleanup"),
    "consistency_check_thread": ("THREAD_CHECK_ENABLED", "enable_thread_check"),
    "consistency_check_voice": ("VOICE_CHECK_ENABLED", "enable_voice_check"),
    "summary_generator": ("SUMMARY_GENERATOR_ENABLED", "enable_summary_gen"),
    "section_evaluate": ("SECTION_EVAL_ENABLED", "enable_thread_check"),
}


class FeatureToggleMiddleware(ExtendedMiddleware):
    """
    统一功能开关中间件（102.02）— 替代各节点中散落的 _is_enabled() 检查。

    通过 TOGGLE_MAP 声明式定义可选节点的开关，
    在 before_node 中检查环境变量 + StyleProfile 双开关，
    不满足条件时设置 _skip_node=True 标记。

    环境变量开关：FEATURE_TOGGLE_ENABLED (default: true)
    """

    def __init__(self, style=None):
        self.style = style

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if os.getenv("FEATURE_TOGGLE_ENABLED", "true").lower() == "false":
            return None

        toggle = TOGGLE_MAP.get(node_name)
        if not toggle:
            return None  # 非可选节点，不拦截

        env_key, style_attr = toggle
        env_enabled = os.getenv(env_key, "true").lower() == "true"
        style = self.style or state.get("_style_profile")
        style_enabled = getattr(style, style_attr, True) if style else True

        if not (env_enabled and style_enabled):
            logger.info("[FeatureToggle] %s 已禁用，跳过", node_name)
            return {"_skip_node": True}
        return None


# ==================== 102.02：GracefulDegradationMiddleware ====================


# 可降级节点白名单及其默认返回值
DEGRADABLE_NODES: Dict[str, Dict[str, Any]] = {
    "factcheck": {},
    "humanizer": {},
    "text_cleanup": {},
    "consistency_check_thread": {"thread_issues": []},
    "consistency_check_voice": {"voice_issues": []},
    "summary_generator": {},
    "section_evaluate": {},
}


class GracefulDegradationMiddleware(ExtendedMiddleware):
    """
    统一降级中间件（102.02）— 替代各节点中散落的 try/except 和 @safe_run。

    在 on_error 中检查节点是否在可降级白名单中，
    是则返回默认值实现优雅降级，否则继续抛出异常。

    环境变量开关：GRACEFUL_DEGRADATION_ENABLED (default: true)
    """

    def on_error(self, state: Dict[str, Any], node_name: str, error: Exception) -> Optional[Dict[str, Any]]:
        if os.getenv("GRACEFUL_DEGRADATION_ENABLED", "true").lower() == "false":
            return None

        if node_name in DEGRADABLE_NODES:
            defaults = DEGRADABLE_NODES[node_name]
            logger.error("[GracefulDegradation] %s 异常，降级跳过: %s", node_name, error)
            return defaults
        return None  # 不处理，继续抛出


# ==================== TaskLogMiddleware ====================


class TaskLogMiddleware:
    """
    任务日志中间件 — 自动记录每个节点的执行耗时到 BlogTaskLog。

    利用 wrap_node 已计算的 _last_duration_ms，在 after_node 中
    调用 task_log.log_step() 写入结构化日志。生成结束后 task log JSON
    中即包含完整的 step 级耗时分解。

    需要在 generator 中通过 set_task_log() 注入 BlogTaskLog 实例。
    """

    def __init__(self):
        self._task_log = None

    def set_task_log(self, task_log):
        self._task_log = task_log

    def before_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        return None

    def after_node(self, state: Dict[str, Any], node_name: str) -> Optional[Dict[str, Any]]:
        if not self._task_log:
            return None
        duration_ms = state.get("_last_duration_ms", 0)
        self._task_log.log_step(
            agent=node_name,
            action="node_complete",
            duration_ms=duration_ms,
        )
        return None
