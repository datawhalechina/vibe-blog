"""
上下文长度动态估算与自动回退

在 LLM 调用前估算 prompt token 数，超限时按优先级裁剪内容。
vibe-blog 是单轮调用场景，回退策略是分段裁剪而非移除对话对。

来源：37.33 MiroThinker 特性改造
"""
import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# 模型上下文窗口配置
MODEL_CONTEXT_LIMITS = {
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    # Anthropic
    "claude-3.5-sonnet": 200_000,
    "claude-3.5-haiku": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    # 通义千问
    "qwen3": 128_000,
    "qwen-max": 128_000,
    "qwen-plus": 128_000,
    "qwen-turbo": 128_000,
    # DeepSeek
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 64_000,
}

# 安全系数
SAFETY_MARGIN_RATIO = float(os.environ.get('CONTEXT_SAFETY_MARGIN', '0.85'))

def estimate_tokens(text: str, method: str = "auto") -> int:
    """
    估算文本的 token 数。

    Args:
        text: 输入文本
        method: "tiktoken" | "char" | "auto"（优先 tiktoken，降级 char）
    """
    if not text:
        return 0

    if method == "char":
        return _estimate_by_chars(text)

    if method in ("tiktoken", "auto"):
        try:
            import tiktoken
            if not hasattr(estimate_tokens, "_encoder"):
                try:
                    estimate_tokens._encoder = tiktoken.get_encoding("o200k_base")
                except Exception:
                    estimate_tokens._encoder = tiktoken.get_encoding("cl100k_base")
            return len(estimate_tokens._encoder.encode(text))
        except ImportError:
            if method == "tiktoken":
                logger.warning("tiktoken 未安装，降级为字符估算")
            return _estimate_by_chars(text)
        except Exception as e:
            logger.warning(f"tiktoken 编码失败: {e}，降级为字符估算")
            return _estimate_by_chars(text)

    return _estimate_by_chars(text)


def _estimate_by_chars(text: str) -> int:
    """按字符数估算 token。中文约 1.5 字/token，英文约 4 字符/token。"""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def get_context_limit(model_name: str) -> int:
    """获取模型的上下文窗口大小（精确匹配 → 前缀匹配 → 默认 128K）"""
    if model_name in MODEL_CONTEXT_LIMITS:
        return MODEL_CONTEXT_LIMITS[model_name]
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if model_name.startswith(key):
            return limit
    logger.warning(f"未知模型 {model_name}，使用默认上下文窗口 128K")
    return 128_000


def get_safe_input_limit(model_name: str, max_output_tokens: int = 4096) -> int:
    """安全 input token 上限 = 上下文窗口 × 安全系数 - max_output_tokens - buffer"""
    context_limit = get_context_limit(model_name)
    safe_limit = int(context_limit * SAFETY_MARGIN_RATIO) - max_output_tokens - 1000
    return max(safe_limit, 4096)


class ContextGuard:
    """
    上下文长度守卫。
    在 LLM 调用前检查 prompt 是否会超限，超限时按优先级自动裁剪内容。
    """

    def __init__(self, model_name: str, max_output_tokens: int = 4096):
        self.model_name = model_name
        self.max_output_tokens = max_output_tokens
        self.safe_input_limit = get_safe_input_limit(model_name, max_output_tokens)
        self.context_limit = get_context_limit(model_name)

    def check(self, messages: list) -> Dict:
        """
        检查消息列表的 token 用量。

        Returns:
            {estimated_tokens, safe_limit, context_limit, usage_ratio, is_safe, overflow_tokens}
        """
        total_text = ""
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total_text += block.get("text", "")
            else:
                total_text += str(content)

        estimated = estimate_tokens(total_text)
        overflow = estimated - self.safe_input_limit

        result = {
            "estimated_tokens": estimated,
            "safe_limit": self.safe_input_limit,
            "context_limit": self.context_limit,
            "usage_ratio": estimated / self.safe_input_limit if self.safe_input_limit > 0 else 0,
            "is_safe": overflow <= 0,
            "overflow_tokens": overflow,
        }

        if overflow > 0:
            logger.warning(
                f"上下文即将超限: {estimated:,} tokens "
                f"(限制 {self.safe_input_limit:,}, 超出 {overflow:,})"
            )

        return result

    def trim_prompt(
        self,
        prompt: str,
        sections: Dict[str, str],
        priority: List[str] = None,
    ) -> Tuple[str, Dict]:
        """
        智能裁剪 prompt 内容，确保不超限。

        Args:
            prompt: 原始 prompt 模板（包含 {section_name} 占位符）
            sections: prompt 中各部分的内容
            priority: 裁剪优先级（从低到高，低优先级先裁）
                默认: ["research", "existing_content", "outline", "instructions"]
        """
        if priority is None:
            priority = ["research", "existing_content", "outline", "instructions"]

        section_tokens = {name: estimate_tokens(content) for name, content in sections.items()}
        total_tokens = sum(section_tokens.values())
        trim_info: Dict = {
            "original_tokens": total_tokens,
            "trimmed_sections": [],
        }

        if total_tokens <= self.safe_input_limit:
            final_prompt = prompt
            for name, content in sections.items():
                final_prompt = final_prompt.replace(f"{{{name}}}", content)
            trim_info["final_tokens"] = total_tokens
            trim_info["trimmed"] = False
            return final_prompt, trim_info

        # 按优先级从低到高裁剪
        overflow = total_tokens - self.safe_input_limit
        trimmed_sections = dict(sections)

        for section_name in priority:
            if overflow <= 0:
                break
            if section_name not in trimmed_sections:
                continue

            content = trimmed_sections[section_name]
            stc = section_tokens[section_name]
            if stc <= 0:
                continue

            if overflow >= stc:
                trimmed_sections[section_name] = f"[{section_name} 已裁剪以适应上下文窗口]"
                overflow -= stc
                trim_info["trimmed_sections"].append(
                    {"section": section_name, "action": "removed", "tokens_saved": stc}
                )
                logger.warning(f"裁剪 [{section_name}]: 整段移除 ({stc:,} tokens)")
            else:
                keep_ratio = 1 - (overflow / stc)
                keep_chars = int(len(content) * keep_ratio)
                trimmed_sections[section_name] = (
                    content[:keep_chars]
                    + f"\n\n... [{section_name} 已截断，保留 {keep_ratio:.0%}] ..."
                )
                tokens_saved = overflow
                overflow = 0
                trim_info["trimmed_sections"].append(
                    {"section": section_name, "action": "truncated",
                     "keep_ratio": keep_ratio, "tokens_saved": tokens_saved}
                )
                logger.warning(f"裁剪 [{section_name}]: 保留 {keep_ratio:.0%} (节省 {tokens_saved:,} tokens)")

        final_prompt = prompt
        for name, content in trimmed_sections.items():
            final_prompt = final_prompt.replace(f"{{{name}}}", content)

        final_tokens = estimate_tokens(final_prompt)
        trim_info["final_tokens"] = final_tokens
        trim_info["trimmed"] = True

        logger.info(f"裁剪完成: {total_tokens:,} -> {final_tokens:,} tokens (节省 {total_tokens - final_tokens:,})")
        return final_prompt, trim_info
