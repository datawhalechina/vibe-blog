"""
跨任务性能摘要统计模块

从多个 BlogTaskLog 中聚合性能数据，支持三个维度的分析：
1. agent_breakdown — 按 Agent 分解耗时和 token
2. cross_cutting_breakdown — 横切面分解（LLM / 搜索 / 图片生成）
3. service_workload — 按服务类型分解调用量

来源：37.08 MiroThinker 特性改造（§八 性能聚合统计）
"""
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class BlogPerformanceSummary:
    """跨任务性能摘要统计"""

    total_tasks: int = 0
    total_wall_time_ms: int = 0

    # 维度 1：按 Agent 分解
    agent_breakdown: Dict[str, Dict] = field(default_factory=lambda: defaultdict(
        lambda: {"duration_ms": 0, "tokens_input": 0, "tokens_output": 0, "steps": 0}
    ))

    # 维度 2：横切面分解（毫秒）
    cross_cutting_breakdown: Dict[str, float] = field(
        default_factory=lambda: defaultdict(float)
    )

    # 维度 3：按服务类型分解调用量
    service_workload: Dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )

    def add_task_log(self, task_log) -> None:
        """从一个 BlogTaskLog 实例中提取数据并累加"""
        self.total_tasks += 1
        self.total_wall_time_ms += getattr(task_log, 'total_duration_ms', 0)

        # 累加 Agent 维度
        for agent_name, stats in getattr(task_log, 'agent_stats', {}).items():
            agg = self.agent_breakdown[agent_name]
            agg["duration_ms"] += stats.get("duration_ms", 0)
            agg["tokens_input"] += stats.get("tokens_input", 0)
            agg["tokens_output"] += stats.get("tokens_output", 0)
            agg["steps"] += stats.get("steps", 0)

        # 累加横切面维度 + 服务调用量
        for step in getattr(task_log, 'steps', []):
            action = step.action if hasattr(step, 'action') else step.get("action", "")
            duration = step.duration_ms if hasattr(step, 'duration_ms') else step.get("duration_ms", 0)

            self.cross_cutting_breakdown[self._classify_action(action)] += duration

            service = self._classify_service(action)
            if service:
                self.service_workload[service] += 1

    @staticmethod
    def _classify_action(action: str) -> str:
        """将 action 分类到横切面维度"""
        a = action.lower()
        if any(k in a for k in ("llm", "chat", "generate_outline", "write_section",
                                 "review", "enhance", "revise")):
            return "llm_call_ms"
        if any(k in a for k in ("search", "research", "scrape")):
            return "search_api_ms"
        if any(k in a for k in ("image", "artist", "draw")):
            return "image_gen_ms"
        return "other_ms"

    @staticmethod
    def _classify_service(action: str) -> Optional[str]:
        """将 action 分类到服务调用量维度"""
        a = action.lower()
        if "search" in a:
            return "search"
        if "scrape" in a:
            return "scrape"
        if any(k in a for k in ("image", "artist", "draw")):
            return "image_generate"
        if any(k in a for k in ("write", "review", "enhance", "outline", "revise")):
            return "llm_chat"
        return None

    def get_averages(self) -> Dict:
        """计算所有维度的平均值"""
        if self.total_tasks == 0:
            return {}
        n = self.total_tasks
        return {
            "avg_wall_time_ms": self.total_wall_time_ms / n,
            "avg_agent_breakdown": {
                agent: {f"avg_{k}": v / n for k, v in stats.items()}
                for agent, stats in self.agent_breakdown.items()
            },
            "avg_cross_cutting": {
                f"avg_{k}": v / n for k, v in self.cross_cutting_breakdown.items()
            },
            "avg_service_workload": {
                f"avg_{k}": v / n for k, v in self.service_workload.items()
            },
        }

    def get_report(self) -> str:
        """生成人类可读的性能摘要报告"""
        if self.total_tasks == 0:
            return "暂无任务数据"

        avg_time = self.total_wall_time_ms / self.total_tasks / 1000
        lines = [
            f"性能摘要统计（共 {self.total_tasks} 个任务）",
            f"  平均总耗时: {avg_time:.1f}s",
            "",
            "  Agent 耗时排行（平均）:",
        ]

        sorted_agents = sorted(
            self.agent_breakdown.items(),
            key=lambda x: x[1]["duration_ms"],
            reverse=True,
        )
        for agent, stats in sorted_agents:
            avg_dur = stats["duration_ms"] / self.total_tasks / 1000
            avg_tokens = (stats["tokens_input"] + stats["tokens_output"]) / self.total_tasks
            pct = stats["duration_ms"] / self.total_wall_time_ms * 100 if self.total_wall_time_ms else 0
            lines.append(
                f"  - {agent}: {avg_dur:.1f}s ({pct:.0f}%) | "
                f"avg {avg_tokens:,.0f} tokens | "
                f"avg {stats['steps']/self.total_tasks:.1f} 步"
            )

        # 横切面分解
        if self.cross_cutting_breakdown:
            lines.append("")
            lines.append("  横切面耗时分解（平均）:")
            total_cross = sum(self.cross_cutting_breakdown.values()) or 1
            label_map = {
                "llm_call_ms": "LLM 调用", "search_api_ms": "搜索 API",
                "image_gen_ms": "图片生成", "other_ms": "其他",
            }
            for cat, total_ms in sorted(self.cross_cutting_breakdown.items(),
                                         key=lambda x: x[1], reverse=True):
                avg_s = total_ms / self.total_tasks / 1000
                pct = total_ms / total_cross * 100
                lines.append(f"  - {label_map.get(cat, cat)}: {avg_s:.1f}s ({pct:.0f}%)")

        # 服务调用量
        if self.service_workload:
            lines.append("")
            lines.append("  服务调用量（平均每次生成）:")
            for svc, count in sorted(self.service_workload.items(),
                                      key=lambda x: x[1], reverse=True):
                lines.append(f"  - {svc}: {count / self.total_tasks:.1f} 次")

        return "\n".join(lines)

    def save(self, output_path: str = None) -> None:
        """保存摘要到 JSON 文件"""
        output_path = output_path or "logs/blog_tasks/performance_summary.json"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        data = {
            "total_tasks": self.total_tasks,
            "total_wall_time_ms": self.total_wall_time_ms,
            "agent_breakdown": dict(self.agent_breakdown),
            "cross_cutting_breakdown": dict(self.cross_cutting_breakdown),
            "service_workload": dict(self.service_workload),
            "averages": self.get_averages(),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def from_log_dir(cls, log_dir: str = "logs/blog_tasks") -> "BlogPerformanceSummary":
        """从日志目录读取所有任务日志并聚合"""
        summary = cls()
        log_path = Path(log_dir)
        if not log_path.exists():
            return summary

        for json_file in sorted(log_path.glob("*.json")):
            if json_file.name == "performance_summary.json":
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                summary.add_task_log(_TaskLogProxy(data))
            except Exception:
                continue

        # 也扫描子文件夹中的 task.json（新格式）
        for json_file in sorted(log_path.glob("*/task.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                summary.add_task_log(_TaskLogProxy(data))
            except Exception:
                continue

        return summary


class _TaskLogProxy:
    """从 JSON dict 构造的轻量代理，模拟 BlogTaskLog 接口"""

    def __init__(self, data: dict):
        self.total_duration_ms = data.get("total_duration_ms", 0)
        self.agent_stats = data.get("agent_stats", {})
        self.target_length = data.get("target_length", "unknown")
        self.steps = data.get("steps", [])
