"""
Token 统计增强 -- 多维聚合（按 Agent + Model 双维度）

增强现有 TokenTracker 的统计能力，提供按 Agent 和 Model 两个维度的
聚合分析，以及 top N 消费者排行。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TokenUsageRecord:
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


class TokenStats:
    """多维 Token 统计聚合器"""

    def __init__(self):
        self._records: List[TokenUsageRecord] = []

    def record(self, agent: str, model: str,
               input_tokens: int = 0, output_tokens: int = 0,
               cached_tokens: int = 0):
        self._records.append(TokenUsageRecord(
            agent=agent, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cached_tokens=cached_tokens,
        ))

    def by_agent(self) -> Dict[str, dict]:
        """按 Agent 聚合"""
        result: Dict[str, dict] = {}
        for r in self._records:
            if r.agent not in result:
                result[r.agent] = {"calls": 0, "input": 0, "output": 0, "cached": 0}
            result[r.agent]["calls"] += 1
            result[r.agent]["input"] += r.input_tokens
            result[r.agent]["output"] += r.output_tokens
            result[r.agent]["cached"] += r.cached_tokens
        return result

    def by_model(self) -> Dict[str, dict]:
        """按 Model 聚合"""
        result: Dict[str, dict] = {}
        for r in self._records:
            if r.model not in result:
                result[r.model] = {"calls": 0, "input": 0, "output": 0, "cached": 0}
            result[r.model]["calls"] += 1
            result[r.model]["input"] += r.input_tokens
            result[r.model]["output"] += r.output_tokens
            result[r.model]["cached"] += r.cached_tokens
        return result

    def total(self) -> dict:
        """总计"""
        return {
            "calls": len(self._records),
            "input": sum(r.input_tokens for r in self._records),
            "output": sum(r.output_tokens for r in self._records),
            "cached": sum(r.cached_tokens for r in self._records),
        }

    def top_consumers(self, n: int = 5, dimension: str = "agent") -> List[dict]:
        """按总 token 排序的 top N"""
        agg = self.by_agent() if dimension == "agent" else self.by_model()
        items = [
            {"name": k, "total": v["input"] + v["output"], **v}
            for k, v in agg.items()
        ]
        return sorted(items, key=lambda x: x["total"], reverse=True)[:n]

    def clear(self):
        self._records.clear()
