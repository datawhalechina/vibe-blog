"""
41.08 成本追踪增强 — USD 成本估算 + 预算熔断

在 TokenTracker 基础上增加：
1. 实时 USD 成本估算（基于 PRICING 表）
2. 预算熔断器（超过阈值自动告警/中断）
3. 限流器指标聚合（从 GlobalRateLimiter 获取等待统计）
4. 成本摘要输出（供 BlogTaskLog 和 SSE 使用）

环境变量：
- COST_TRACKING_ENABLED: 是否启用成本追踪（默认 false）
- COST_BUDGET_USD: 单次生成预算上限（USD，默认 2.0）
- COST_BUDGET_ACTION: 超预算动作 warn / abort（默认 warn）
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CostTracker:
    """任务级成本追踪器，包装 TokenTracker 提供 USD 成本视图。"""

    budget_usd: float = 0.0
    budget_action: str = "warn"  # warn | abort
    _accumulated_cost: float = 0.0
    _budget_exceeded: bool = False
    _cost_by_agent: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.budget_usd <= 0:
            self.budget_usd = float(os.environ.get('COST_BUDGET_USD', '2.0'))
        if not self.budget_action:
            self.budget_action = os.environ.get('COST_BUDGET_ACTION', 'warn')

    def record_call(self, input_tokens: int, output_tokens: int,
                    cache_read_tokens: int = 0, cache_write_tokens: int = 0,
                    model: str = "", agent: str = "unknown"):
        """记录一次 LLM 调用的成本"""
        from utils.token_tracker import _match_pricing
        prices = _match_pricing(model)
        if not prices:
            return

        cost = (
            input_tokens * prices.get("input", 0)
            + output_tokens * prices.get("output", 0)
            + cache_read_tokens * prices.get("cache_read", 0)
            + cache_write_tokens * prices.get("cache_write", 0)
        ) / 1_000_000

        self._accumulated_cost += cost
        self._cost_by_agent[agent] = self._cost_by_agent.get(agent, 0.0) + cost

        # 预算检查
        if not self._budget_exceeded and self._accumulated_cost > self.budget_usd:
            self._budget_exceeded = True
            if self.budget_action == "abort":
                logger.error(
                    f"[CostTracker] 预算超限! ${self._accumulated_cost:.4f} > ${self.budget_usd:.2f}，中断生成"
                )
                raise BudgetExceededError(
                    f"成本 ${self._accumulated_cost:.4f} 超过预算 ${self.budget_usd:.2f}"
                )
            else:
                logger.warning(
                    f"[CostTracker] 预算告警: ${self._accumulated_cost:.4f} > ${self.budget_usd:.2f}"
                )

    def get_summary(self) -> Dict:
        """获取成本摘要"""
        rate_limiter_metrics = {}
        try:
            from utils.rate_limiter import get_global_rate_limiter
            rate_limiter_metrics = get_global_rate_limiter().get_metrics()
        except Exception:
            pass

        return {
            "total_cost_usd": round(self._accumulated_cost, 6),
            "budget_usd": self.budget_usd,
            "budget_exceeded": self._budget_exceeded,
            "cost_by_agent": {k: round(v, 6) for k, v in self._cost_by_agent.items()},
            "rate_limiter_metrics": rate_limiter_metrics,
        }

    def format_summary(self) -> str:
        """格式化成本摘要"""
        lines = [
            "",
            "─" * 20 + " Cost Summary " + "─" * 20,
            f"  Total Cost:   ${self._accumulated_cost:.4f} USD",
            f"  Budget:       ${self.budget_usd:.2f} USD",
            f"  Budget Used:  {self._accumulated_cost / max(self.budget_usd, 0.01) * 100:.1f}%",
        ]
        if self._cost_by_agent:
            lines.append("  Agent Breakdown:")
            for agent, cost in sorted(self._cost_by_agent.items(), key=lambda x: -x[1]):
                lines.append(f"    {agent:>16}: ${cost:.4f}")
        lines.append("─" * 54)
        return "\n".join(lines)


class BudgetExceededError(Exception):
    """预算超限异常"""
    pass
