"""
SessionTracker — 业务级状态追踪（基于 Langfuse）

在已有 Langfuse LLM 调用追踪基础上，叠加业务级状态追踪：
  - 迭代快照（深化/修订前后的内容变化）
  - 质量分数趋势（Reviewer/Questioner 每轮打分）
  - 配图生成记录（成功/失败/重试）
  - 段落评估分数（69.04 Generator-Critic Loop）

核心原则：零新增依赖，完全复用已有 Langfuse 集成。
失败不影响正常流程（所有操作 try/except 包裹）。
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 仅在 TRACE_ENABLED=true 时启用追踪
_TRACE_ENABLED = os.environ.get("TRACE_ENABLED", "false").lower() == "true"


def _get_langfuse():
    """获取 Langfuse 客户端（懒加载）"""
    if not _TRACE_ENABLED:
        return None
    try:
        from langfuse import Langfuse
        return Langfuse()
    except Exception:
        return None


class SessionTracker:
    """业务级状态追踪器"""

    def __init__(self, trace_id: str = ""):
        self.trace_id = trace_id
        self._langfuse = _get_langfuse()
        self._enabled = self._langfuse is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def log_score(self, name: str, value: float, comment: str = ""):
        """记录质量分数到 Langfuse Score"""
        if not self._enabled:
            return
        try:
            kwargs = {"name": name, "value": value}
            if comment:
                kwargs["comment"] = comment
            if self.trace_id:
                kwargs["trace_id"] = self.trace_id
            # Langfuse v3: score() 可能不在顶层对象上
            if hasattr(self._langfuse, 'score'):
                self._langfuse.score(**kwargs)
        except Exception as e:
            logger.debug(f"SessionTracker.log_score 失败: {e}")

    def log_event(self, name: str, metadata: Dict[str, Any] = None):
        """记录业务事件到 Langfuse Trace"""
        if not self._enabled:
            return
        try:
            if hasattr(self._langfuse, 'trace'):
                self._langfuse.trace(
                    name=name,
                    metadata=metadata or {},
                )
        except Exception as e:
            logger.debug(f"SessionTracker.log_event 失败: {e}")

    # ------------------------------------------------------------------
    # 便捷方法：常见业务场景
    # ------------------------------------------------------------------

    def log_review_score(self, score: int, round_num: int, summary: str = ""):
        """记录 Reviewer 审核分数"""
        self.log_score(
            name="review_score",
            value=score / 100.0,
            comment=f"Round {round_num}: {summary[:100]}",
        )

    def log_depth_score(self, section_title: str, score: int):
        """记录 Questioner 深度分数"""
        self.log_score(
            name="depth_score",
            value=score / 100.0,
            comment=section_title[:50],
        )

    def log_section_evaluation(
        self, section_title: str, scores: Dict[str, float], overall: float
    ):
        """记录段落评估分数（69.04）"""
        self.log_score(
            name="section_quality",
            value=overall / 10.0,
            comment=f"{section_title}: {scores}",
        )

    def log_image_generation(
        self, image_id: str, image_type: str, success: bool, error: str = ""
    ):
        """记录配图生成结果"""
        self.log_score(
            name="image_generation",
            value=1.0 if success else 0.0,
            comment=f"{image_type}:{image_id}" + (f" error={error[:80]}" if error else ""),
        )

    def log_deepen_snapshot(
        self, round_num: int, sections_deepened: int, chars_added: int
    ):
        """记录深化迭代快照"""
        self.log_event(
            name=f"deepen_round_{round_num}",
            metadata={
                "round": round_num,
                "sections_deepened": sections_deepened,
                "chars_added": chars_added,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def log_section_improve_snapshot(
        self, round_num: int, improved_count: int, avg_score_before: float, avg_score_after: float
    ):
        """记录段落改进迭代快照"""
        self.log_event(
            name=f"section_improve_round_{round_num}",
            metadata={
                "round": round_num,
                "improved_count": improved_count,
                "avg_score_before": round(avg_score_before, 2),
                "avg_score_after": round(avg_score_after, 2),
                "delta": round(avg_score_after - avg_score_before, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
