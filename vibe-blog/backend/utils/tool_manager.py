"""
统一工具管理器 — BlogToolManager

轻量级 Python 函数注册，统一管理搜索、图片生成、视频生成等工具的
注册、执行、超时保护和日志。不引入 MCP 协议。

来源：37.09 MiroThinker ToolManager 迁移
"""
import logging
import os
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    func: Callable
    description: str
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


class BlogToolManager:
    """
    博客生成工具管理器

    功能：
    1. 统一工具注册和发现
    2. 工具黑名单
    3. 超时保护（threading 实现，适配 Flask 同步架构）
    4. 执行日志（集成 BlogTaskLog）
    5. 执行统计
    """

    def __init__(
        self,
        blacklist: Set[str] = None,
        task_log=None,
    ):
        self._tools: Dict[str, ToolDefinition] = {}
        self._blacklist: Set[str] = blacklist or set()
        self._task_log = task_log
        self._execution_log: List[Dict] = []

        # 从环境变量读取黑名单
        env_bl = os.environ.get("TOOL_BLACKLIST", "")
        if env_bl:
            self._blacklist.update(n.strip() for n in env_bl.split(",") if n.strip())

    # ---- 注册 ----

    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        timeout: int = None,
        **metadata,
    ) -> None:
        """注册工具"""
        default_timeout = int(os.environ.get("TOOL_DEFAULT_TIMEOUT", "300"))
        self._tools[name] = ToolDefinition(
            name=name,
            func=func,
            description=description,
            timeout=timeout or default_timeout,
            metadata=metadata,
        )
        logger.debug(f"注册工具: {name}")

    def register_decorator(self, name: str, description: str = "", timeout: int = None):
        """装饰器方式注册工具"""
        def decorator(func):
            self.register(name, func, description=description, timeout=timeout)
            return func
        return decorator

    # ---- 发现 ----

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """返回所有可用工具（排除黑名单）"""
        return [
            {"name": td.name, "description": td.description, "timeout": td.timeout}
            for td in self._tools.values()
            if td.name not in self._blacklist
        ]

    # ---- 参数自动修复 ----

    # 工具参数别名映射：{tool_name: {wrong_param: correct_param}}
    _PARAM_ALIASES: Dict[str, Dict[str, str]] = {
        "web_search": {"q": "query", "keyword": "query", "keywords": "query"},
        "deep_scrape": {"description": "info_to_extract", "introduction": "info_to_extract"},
    }

    def fix_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        修正 LLM 常见的参数名错误

        来源：MiroThinker fix_tool_call_arguments()
        """
        aliases = self._PARAM_ALIASES.get(tool_name, {})
        if not aliases:
            return arguments
        fixed = arguments.copy()
        for wrong, correct in aliases.items():
            if correct not in fixed and wrong in fixed:
                fixed[correct] = fixed.pop(wrong)
                logger.debug(f"参数修正: {tool_name}.{wrong} → {correct}")
        return fixed

    # ---- 执行 ----

    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具（带超时保护、错误处理、日志）

        Returns:
            {"success": bool, "result": Any, "error": str, "duration_ms": int}
        """
        if name not in self._tools:
            return {"success": False, "result": None, "error": f"Tool not found: {name}", "duration_ms": 0}

        tool = self._tools[name]

        if name in self._blacklist:
            return {"success": False, "result": None, "error": f"Tool blacklisted: {name}", "duration_ms": 0}

        # 参数自动修复
        kwargs = self.fix_arguments(name, kwargs)

        start = time.time()
        result_holder = [None]
        error_holder = [None]

        def _run():
            try:
                result_holder[0] = tool.func(**kwargs)
            except Exception as e:
                error_holder[0] = e

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=tool.timeout)

        duration_ms = int((time.time() - start) * 1000)

        if thread.is_alive():
            # 超时
            self._record(name, duration_ms, success=False, error="timeout")
            self._log_to_task_log(name, duration_ms, level="error", detail=f"Timeout after {tool.timeout}s")
            return {"success": False, "result": None, "error": f"Timeout after {tool.timeout}s", "duration_ms": duration_ms}

        if error_holder[0] is not None:
            err_msg = str(error_holder[0])
            self._record(name, duration_ms, success=False, error=err_msg)
            self._log_to_task_log(name, duration_ms, level="error", detail=err_msg)
            return {"success": False, "result": None, "error": err_msg, "duration_ms": duration_ms}

        self._record(name, duration_ms, success=True)
        self._log_to_task_log(name, duration_ms, level="info")
        return {"success": True, "result": result_holder[0], "error": "", "duration_ms": duration_ms}

    # ---- 日志 ----

    def set_task_log(self, task_log) -> None:
        """注入 BlogTaskLog"""
        self._task_log = task_log

    def _log_to_task_log(self, tool_name: str, duration_ms: int, level: str = "info", detail: str = ""):
        if self._task_log:
            try:
                self._task_log.log_step(
                    "tool_manager", tool_name,
                    level=level, detail=detail, duration_ms=duration_ms,
                )
            except Exception:
                pass

    def _record(self, tool_name: str, duration_ms: int, success: bool, error: str = ""):
        self._execution_log.append({
            "tool": tool_name,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
            "timestamp": time.time(),
        })

    def get_execution_stats(self) -> Dict[str, Dict]:
        """获取执行统计"""
        stats: Dict[str, Dict] = {}
        for log in self._execution_log:
            t = log["tool"]
            if t not in stats:
                stats[t] = {"calls": 0, "successes": 0, "failures": 0, "total_ms": 0}
            stats[t]["calls"] += 1
            stats[t]["total_ms"] += log["duration_ms"]
            if log["success"]:
                stats[t]["successes"] += 1
            else:
                stats[t]["failures"] += 1
        for s in stats.values():
            s["avg_ms"] = s["total_ms"] // s["calls"] if s["calls"] else 0
        return stats
