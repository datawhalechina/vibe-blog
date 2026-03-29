"""
全局日志配置（带任务上下文与 Rich 彩色输出）
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import Iterable

# 任务 ID 上下文变量（供异步任务链路注入）
task_id_context: ContextVar[str] = ContextVar("task_id", default="")


class TaskIdFilter(logging.Filter):
    """为日志记录注入 task_id 字段，避免格式化时报 KeyError。"""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        task_id = task_id_context.get()
        record.task_id = f"[{task_id}]" if task_id else ""
        return True


class RichLevelFormatter(logging.Formatter):
    """在控制台为 levelname 注入 rich markup 颜色（文件日志仍为纯文本）。"""

    LEVEL_STYLES = {
        logging.DEBUG: "dim",
        logging.INFO: "green",
        logging.WARNING: "yellow",
        logging.ERROR: "bold red",
        logging.CRITICAL: "bold white on red",
    }

    def __init__(self, *args, enable_markup: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.enable_markup = enable_markup

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        if not self.enable_markup:
            return super().format(record)

        original_levelname = record.levelname
        style = self.LEVEL_STYLES.get(record.levelno)
        if style:
            record.levelname = f"[{style}]{original_levelname}[/]"
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.INFO)


def _iter_vibe_handlers(handlers: Iterable[logging.Handler]) -> list[logging.Handler]:
    return [h for h in handlers if getattr(h, "_vibe_blog_handler", False)]


def _ensure_task_filter(root_logger: logging.Logger) -> TaskIdFilter:
    for f in root_logger.filters:
        if isinstance(f, TaskIdFilter):
            return f
    task_filter = TaskIdFilter()
    task_filter._vibe_blog_filter = True  # type: ignore[attr-defined]
    root_logger.addFilter(task_filter)
    return task_filter


def setup_logging(log_level: str | int = "INFO", log_dir: str | None = None, enable_file: bool = True) -> None:
    """
    配置全局日志：
    1) 控制台使用 Rich 彩色输出（若 rich 不可用则自动降级）
    2) 文件日志保留 DEBUG 级别（在可写环境下）
    3) 注入 task_id 上下文字段
    """

    level = _resolve_level(log_level)
    root_logger = logging.getLogger()

    # 放开 root 级别，让 handler 自己控流量（否则 DEBUG 文件日志会被 root 卡掉）
    root_logger.setLevel(logging.DEBUG)
    task_filter = _ensure_task_filter(root_logger)

    existing_handlers = _iter_vibe_handlers(root_logger.handlers)
    if existing_handlers:
        # 已配置过：只更新级别，避免重复添加 handler
        for handler in existing_handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)
            else:
                handler.setLevel(level)
        return

    fmt = "%(asctime)s %(task_id)s - %(name)s - %(levelname)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    plain_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # 控制台 handler：优先 Rich
    console_handler: logging.Handler
    console_formatter: logging.Formatter = plain_formatter
    try:
        from rich.console import Console
        from rich.logging import RichHandler

        console = Console(stderr=True, color_system="auto")
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=False,
            show_level=False,
            show_path=False,
            markup=True,
        )
        console_formatter = RichLevelFormatter(fmt=fmt, datefmt=datefmt, enable_markup=True)
    except Exception:
        console_handler = logging.StreamHandler()

    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(task_filter)
    console_handler._vibe_blog_handler = True  # type: ignore[attr-defined]
    root_logger.addHandler(console_handler)

    # 屏蔽高频噪音日志
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("fsevents").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("openai._base_client").setLevel(logging.INFO)

    if not enable_file:
        return

    # 文件 handler：在只读环境（如 Vercel）下自动跳过
    try:
        base_dir = os.path.dirname(os.path.realpath(__file__))
        # 统一日志目录到 vibe-blog/logs/（与启动脚本一致）
        project_root = os.path.dirname(base_dir)
        resolved_log_dir = log_dir or os.path.join(project_root, "logs")
        os.makedirs(resolved_log_dir, exist_ok=True)

        log_file = os.path.join(resolved_log_dir, "app.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(plain_formatter)
        file_handler.addFilter(task_filter)
        file_handler._vibe_blog_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(file_handler)
    except (OSError, IOError):
        # 只读文件系统：保留控制台日志即可
        return


def get_logger(name: str) -> logging.Logger:
    """统一入口，便于未来切换日志实现。"""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# 按任务分离日志
# ---------------------------------------------------------------------------

class TaskIdMatchFilter(logging.Filter):
    """只放行指定 task_id 的日志记录。"""

    def __init__(self, task_id: str) -> None:
        super().__init__()
        self.task_id = task_id

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        return getattr(record, "task_id", "") == f"[{self.task_id}]"


def create_task_logger(task_id: str, log_dir: str | None = None) -> logging.Handler:
    """为指定任务创建独立的文件日志 handler。

    日志写入 ``logs/blog_tasks/{task_id}/task.log``。
    返回 handler 实例，调用方需在任务结束后调用 ``remove_task_logger`` 清理。
    """
    base_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.dirname(base_dir)
    resolved_log_dir = log_dir or os.path.join(project_root, "logs", "blog_tasks")
    task_dir = os.path.join(resolved_log_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    handler = logging.FileHandler(
        os.path.join(task_dir, "task.log"), encoding="utf-8"
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    handler.addFilter(TaskIdMatchFilter(task_id))
    handler._vibe_blog_task_handler = True  # type: ignore[attr-defined]

    root_logger = logging.getLogger()
    _ensure_task_filter(root_logger)  # 确保 TaskIdFilter 已注入
    root_logger.addHandler(handler)
    return handler


def remove_task_logger(handler: logging.Handler) -> None:
    """移除并关闭任务日志 handler。"""
    try:
        logging.getLogger().removeHandler(handler)
        handler.close()
    except Exception:
        pass

