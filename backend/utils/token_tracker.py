"""
统一 Token 追踪与成本分析模块

从 LangChain AIMessage 的 usage_metadata 中提取精确 token 数据（含缓存 token），
通过 TokenTracker 累计统计，支持按 Agent 分组和成本估算。

来源：37.31 MiroThinker 特性改造
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============ 数据结构 ============

@dataclass
class TokenUsage:
    """单次 LLM 调用的 token 用量"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    model: str = ""
    provider: str = ""  # openai / anthropic / zhipu / deepseek

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class TokenTracker:
    """
    任务级 token 追踪器。

    每次博客生成创建一个实例，累计所有 LLM 调用的 token 用量。
    支持按 Agent 分组统计。
    """

    # 累计 token
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_write_tokens: int = 0

    # 按 Agent 分组
    agent_usage: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # 调用历史
    call_history: List[TokenUsage] = field(default_factory=list)

    # 最近一次调用
    last_call: Optional[TokenUsage] = None

    def record(self, usage: TokenUsage, agent: str = "unknown"):
        """
        记录一次 LLM 调用的 token 用量。

        Args:
            usage: 单次调用的 token 用量
            agent: 调用方 Agent 名称
        """
        # 累计
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_cache_read_tokens += usage.cache_read_tokens
        self.total_cache_write_tokens += usage.cache_write_tokens

        # 按 Agent 分组
        if agent not in self.agent_usage:
            self.agent_usage[agent] = {
                "input": 0, "output": 0,
                "cache_read": 0, "cache_write": 0,
                "calls": 0,
            }
        stats = self.agent_usage[agent]
        stats["input"] += usage.input_tokens
        stats["output"] += usage.output_tokens
        stats["cache_read"] += usage.cache_read_tokens
        stats["cache_write"] += usage.cache_write_tokens
        stats["calls"] += 1

        # 记录历史和最近一次
        self.call_history.append(usage)
        self.last_call = usage

        logger.debug(
            f"[{agent}] Token: "
            f"in={usage.input_tokens} out={usage.output_tokens} "
            f"cache_r={usage.cache_read_tokens} cache_w={usage.cache_write_tokens}"
        )

    def get_summary(self) -> Dict:
        """获取汇总数据（供 BlogTaskLog 使用）"""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_calls": len(self.call_history),
            "agent_breakdown": dict(self.agent_usage),
        }

    def format_summary(self) -> str:
        """格式化输出 token 摘要"""
        lines = [
            "",
            "─" * 20 + " Token Usage " + "─" * 20,
            f"  Input Tokens:       {self.total_input_tokens:>10,}",
            f"  Output Tokens:      {self.total_output_tokens:>10,}",
            f"  Cache Read Tokens:  {self.total_cache_read_tokens:>10,}",
            f"  Cache Write Tokens: {self.total_cache_write_tokens:>10,}",
            f"  Total Tokens:       {self.total_input_tokens + self.total_output_tokens:>10,}",
            f"  LLM Calls:          {len(self.call_history):>10}",
            "─" * 53,
        ]

        if self.agent_usage:
            lines.append("  Agent Breakdown:")
            for agent, stats in sorted(
                self.agent_usage.items(),
                key=lambda x: x[1]["input"] + x[1]["output"],
                reverse=True,
            ):
                total = stats["input"] + stats["output"]
                lines.append(
                    f"    {agent:>12}: {total:>8,} tokens "
                    f"({stats['calls']} calls)"
                )

        return "\n".join(lines)


# ============ Token 提取函数 ============

def extract_token_usage_from_langchain(
    response,
    model: str = "",
    provider: str = "",
) -> TokenUsage:
    """
    从 LangChain AIMessage 的 usage_metadata 中提取精确 token 数据。

    支持 3 种响应格式：
    1. LangChain AIMessage（usage_metadata）
    2. 原始 OpenAI 响应（usage.prompt_tokens）
    3. 原始 Anthropic 响应（usage.input_tokens + cache 字段）
    """
    usage = TokenUsage(model=model, provider=provider)

    try:
        # 格式 1: LangChain AIMessage（优先）
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            usage.input_tokens = meta.get("input_tokens", 0) or 0
            usage.output_tokens = meta.get("output_tokens", 0) or 0

            # 缓存 token（不同提供商字段不同）
            details = meta.get("input_token_details", {}) or {}
            if details:
                # Anthropic 格式
                usage.cache_read_tokens = details.get("cache_read", 0) or 0
                usage.cache_write_tokens = details.get("cache_creation", 0) or 0
                # OpenAI 格式（cached 字段）
                if not usage.cache_read_tokens:
                    usage.cache_read_tokens = details.get("cached", 0) or 0

        # 格式 2: 原始 OpenAI 响应
        elif hasattr(response, "usage") and response.usage:
            u = response.usage
            usage.input_tokens = getattr(u, "prompt_tokens", 0) or 0
            usage.output_tokens = getattr(u, "completion_tokens", 0) or 0
            details = getattr(u, "prompt_tokens_details", None)
            if details:
                usage.cache_read_tokens = getattr(details, "cached_tokens", 0) or 0

    except Exception as e:
        logger.warning(f"Token 提取异常（不影响流程）: {e}")

    return usage


# ============ 成本估算 ============

# 主流模型单价（USD / 1M tokens）
PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3.5-haiku": {"input": 0.80, "output": 4.00, "cache_read": 0.08, "cache_write": 1.00},
    "qwen-max": {"input": 0.56, "output": 1.68},
    "deepseek-chat": {"input": 0.14, "output": 0.28, "cache_read": 0.014},
}


def estimate_cost(tracker: TokenTracker) -> float:
    """估算总成本（USD）"""
    total_cost = 0.0
    for call in tracker.call_history:
        prices = _match_pricing(call.model)
        if not prices:
            continue
        total_cost += (
            call.input_tokens * prices.get("input", 0)
            + call.output_tokens * prices.get("output", 0)
            + call.cache_read_tokens * prices.get("cache_read", 0)
            + call.cache_write_tokens * prices.get("cache_write", 0)
        ) / 1_000_000
    return total_cost


def _match_pricing(model_name: str) -> Dict[str, float]:
    """匹配模型定价（支持精确匹配和前缀匹配）"""
    if not model_name:
        return {}
    if model_name in PRICING:
        return PRICING[model_name]
    # 前缀匹配
    for key in PRICING:
        if model_name.startswith(key):
            return PRICING[key]
    return {}
