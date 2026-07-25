"""
结构化任务日志模块 — BlogTaskLog + StepLog + StepTimer

记录每篇博客的完整生成过程：每个 Agent 的步骤、token 用量、执行时间。
任务完成后持久化为 JSON 文件。

来源：37.08 MiroThinker 特性改造
"""
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from infrastructure.paths import RuntimePaths

logger = logging.getLogger(__name__)


@dataclass
class StepLog:
    """单步日志"""
    timestamp: str = ""
    agent: str = ""
    action: str = ""
    level: str = "info"
    detail: str = ""
    duration_ms: int = 0
    tokens: Dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlogTaskLog:
    """
    博客生成任务日志 — 结构化记录整个生成过程。

    每次博客生成创建一个实例，记录所有 Agent 的执行步骤、
    token 用量、执行时间。生成完成后保存为 JSON 文件。
    """

    task_id: str = ""
    topic: str = ""
    article_type: str = ""
    target_length: str = ""
    start_time: str = ""
    end_time: str = ""
    status: str = "running"

    steps: List[StepLog] = field(default_factory=list)
    total_tokens: Dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    total_duration_ms: int = 0
    agent_stats: Dict[str, Dict] = field(default_factory=dict)

    # 质量指标
    final_score: float = 0.0
    revision_rounds: int = 0
    word_count: int = 0

    # token 追踪摘要（由 37.31 TokenTracker 注入）
    token_summary: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now().isoformat()
        if not self.task_id:
            self.task_id = f"blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def log_step(
        self,
        agent: str,
        action: str,
        detail: str = "",
        level: str = "info",
        duration_ms: int = 0,
        tokens: Dict[str, int] = None,
        **metadata,
    ):
        """记录一个执行步骤"""
        step = StepLog(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            action=action,
            level=level,
            detail=detail[:500] if detail else "",
            duration_ms=duration_ms,
            tokens=tokens or {"input": 0, "output": 0},
            metadata=metadata,
        )
        self.steps.append(step)

        # 更新汇总
        if tokens:
            self.total_tokens["input"] += tokens.get("input", 0)
            self.total_tokens["output"] += tokens.get("output", 0)
        self.total_duration_ms += duration_ms

        # 更新 Agent 统计
        if agent not in self.agent_stats:
            self.agent_stats[agent] = {
                "steps": 0, "tokens_input": 0, "tokens_output": 0, "duration_ms": 0,
            }
        stats = self.agent_stats[agent]
        stats["steps"] += 1
        stats["duration_ms"] += duration_ms
        if tokens:
            stats["tokens_input"] += tokens.get("input", 0)
            stats["tokens_output"] += tokens.get("output", 0)

        # 控制台输出
        icon = {"info": "✅", "warning": "⚠️", "error": "❌"}.get(level, "📝")
        token_info = f" | {tokens['input']}+{tokens['output']}tok" if tokens else ""
        time_info = f" | {duration_ms}ms" if duration_ms else ""
        logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"{icon} [{agent}] {action}{time_info}{token_info}"
        )

    def complete(self, score: float = 0, word_count: int = 0, revision_rounds: int = 0):
        """标记任务完成"""
        self.status = "completed"
        self.end_time = datetime.now().isoformat()
        self.final_score = score
        self.word_count = word_count
        self.revision_rounds = revision_rounds

    def fail(self, error: str = ""):
        """标记任务失败"""
        self.status = "failed"
        self.end_time = datetime.now().isoformat()
        self.log_step("system", "task_failed", error, level="error")

    def save(self, logs_dir: str = None) -> str:
        """保存为 JSON 文件到 var/logs/blog_tasks/{task_id}/task.json"""
        if logs_dir:
            base_logs_dir = logs_dir
        elif os.environ.get("BLOG_LOGS_DIR"):
            base_logs_dir = os.environ["BLOG_LOGS_DIR"]
        else:
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            base_logs_dir = str(
                RuntimePaths.from_env(project_root=project_root).logs / "blog_tasks"
            )
        task_dir = Path(base_logs_dir) / self.task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        path = task_dir / "task.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

        logger.info(f"任务日志已保存: {path}")
        return str(path)

    def get_summary(self) -> str:
        """生成人类可读的摘要"""
        total_tok = self.total_tokens["input"] + self.total_tokens["output"]
        lines = [
            f"博客生成报告 [{self.task_id}]",
            f"  主题: {self.topic}",
            f"  状态: {self.status}",
            f"  总用时: {self.total_duration_ms / 1000:.1f}s",
            f"  总 Token: {total_tok:,}",
            f"  修订轮数: {self.revision_rounds}",
            f"  最终分数: {self.final_score}/10",
            f"  字数: {self.word_count:,}",
        ]

        if self.agent_stats:
            lines.append("  Agent 统计:")
            for agent, stats in sorted(
                self.agent_stats.items(),
                key=lambda x: x[1]["duration_ms"],
                reverse=True,
            ):
                total_tokens = stats["tokens_input"] + stats["tokens_output"]
                lines.append(
                    f"  - {agent}: {stats['steps']}步 | "
                    f"{stats['duration_ms']/1000:.1f}s | "
                    f"{total_tokens:,} tokens"
                )

        return "\n".join(lines)


class StepTimer:
    """步骤计时器（上下文管理器）"""

    def __init__(self, task_log: BlogTaskLog, agent: str, action: str, **metadata):
        self.task_log = task_log
        self.agent = agent
        self.action = action
        self.metadata = metadata
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self._start) * 1000)
        level = "error" if exc_type else "info"
        detail = str(exc_val)[:200] if exc_val else ""

        self.task_log.log_step(
            agent=self.agent,
            action=self.action,
            detail=detail,
            level=level,
            duration_ms=duration_ms,
            **self.metadata,
        )

        return False  # 不吞异常
