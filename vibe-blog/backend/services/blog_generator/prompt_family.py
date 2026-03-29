"""
41.16 PromptFamily 统一管理 — 按模型家族适配 Prompt 格式

不同 LLM 家族对文档上下文注入有不同的最优格式：
- Claude: XML 标签包裹 (<context>...</context>)
- OpenAI: Markdown 分隔符
- Qwen: 简洁文本格式

通过 PromptFamily 多态层，在现有 Jinja2 模板系统之上增加模型级适配。

环境变量：
- PROMPT_FAMILY_ENABLED: 是否启用（默认 false）
- PROMPT_FAMILY: 强制指定家族（auto / claude / openai / qwen，默认 auto）
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class BlogPromptFamily:
    """Prompt 家族基类 — 定义模型级适配接口"""

    family_name: str = "default"

    def format_context(self, context: str, label: str = "context") -> str:
        """格式化文档上下文注入"""
        return f"\n---\n{label}:\n{context}\n---\n"

    def get_system_preamble(self) -> str:
        """获取系统级前言（注入到 system message 开头）"""
        return ""

    def get_tone_instruction(self, tone: str) -> str:
        """获取语气指令"""
        return f"请使用{tone}的语气撰写。"

    def wrap_prompt(self, prompt: str) -> str:
        """最终包装 prompt"""
        return prompt


class ClaudePromptFamily(BlogPromptFamily):
    """Claude 家族 — XML 标签格式"""

    family_name = "claude"

    def format_context(self, context: str, label: str = "context") -> str:
        return f"\n<{label}>\n{context}\n</{label}>\n"

    def get_system_preamble(self) -> str:
        return "You are a professional blog writer. Think step by step."

    def get_tone_instruction(self, tone: str) -> str:
        tone_map = {
            "professional": "使用专业、严谨的语气，适合技术读者。",
            "casual": "使用轻松、亲切的语气，像朋友间的对话。",
            "academic": "使用学术、规范的语气，注重论证和引用。",
        }
        return tone_map.get(tone, f"请使用{tone}的语气撰写。")


class OpenAIPromptFamily(BlogPromptFamily):
    """OpenAI 家族 — Markdown 分隔符格式"""

    family_name = "openai"

    def format_context(self, context: str, label: str = "context") -> str:
        return f"\n### {label}\n\n{context}\n\n---\n"

    def get_system_preamble(self) -> str:
        return "You are a professional blog writer."


class QwenPromptFamily(BlogPromptFamily):
    """Qwen 家族 — 简洁文本格式"""

    family_name = "qwen"

    def format_context(self, context: str, label: str = "context") -> str:
        return f"\n【{label}】\n{context}\n"

    def get_tone_instruction(self, tone: str) -> str:
        return f"写作风格：{tone}"


# 家族注册表
_FAMILIES = {
    "claude": ClaudePromptFamily,
    "openai": OpenAIPromptFamily,
    "qwen": QwenPromptFamily,
    "default": BlogPromptFamily,
}


def detect_family(model_name: str) -> str:
    """根据模型名称自动检测家族"""
    if not model_name:
        return "default"
    name = model_name.lower()
    if "claude" in name:
        return "claude"
    if "gpt" in name or "o1" in name or "o3" in name:
        return "openai"
    if "qwen" in name or "tongyi" in name:
        return "qwen"
    if "deepseek" in name:
        return "openai"  # DeepSeek 兼容 OpenAI 格式
    return "default"


def get_prompt_family(model_name: str = "") -> BlogPromptFamily:
    """获取当前模型对应的 PromptFamily 实例"""
    if os.environ.get('PROMPT_FAMILY_ENABLED', 'false').lower() != 'true':
        return BlogPromptFamily()

    forced = os.environ.get('PROMPT_FAMILY', 'auto')
    if forced != 'auto' and forced in _FAMILIES:
        family_cls = _FAMILIES[forced]
    else:
        family_key = detect_family(model_name)
        family_cls = _FAMILIES.get(family_key, BlogPromptFamily)

    return family_cls()
