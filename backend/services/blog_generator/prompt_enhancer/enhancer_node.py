"""
Prompt 增强器核心节点 — 将用户 prompt 通过 AI 重写为高质量写作指令。

功能：
- 意图识别：分析用户输入的核心意图
- 关键词扩展：补充技术细节、应用场景
- 结构化输出：XML 标签解析 + fallback 前缀移除
- 上下文注入：支持 context / article_style 参数
"""
import logging
import re
from typing import Any, Dict

from infrastructure.prompts.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)

# XML 提取正则 — 与 DeerFlow 保持一致
_XML_PATTERN = re.compile(
    r"<enhanced_prompt>(.*?)</enhanced_prompt>",
    re.DOTALL,
)

# Fallback 前缀列表
_PREFIXES_TO_REMOVE = [
    "Enhanced Prompt:",
    "Enhanced prompt:",
    "enhanced prompt:",
    "优化后的主题：",
    "增强后的 Prompt：",
    "增强后的Prompt：",
]


def prompt_enhancer_node(state: Dict[str, Any], llm_service) -> Dict[str, Any]:
    """
    核心增强节点 — 将用户 prompt 通过 AI 重写为高质量写作指令。

    Args:
        state: PromptEnhancerState 字典
        llm_service: LLMService 实例（需有 chat 方法）

    Returns:
        {"output": enhanced_prompt}
    """
    logger.info("Enhancing user prompt...")

    prompt_mgr = get_prompt_manager()

    # 1. 渲染 Jinja2 模板
    try:
        system_prompt = prompt_mgr.render(
            "blog/prompt_enhancer",
            prompt=state["prompt"],
            context=state.get("context", ""),
            article_style=state.get("article_style", ""),
        )
    except Exception as e:
        logger.warning(f"Template render failed, using fallback: {e}")
        system_prompt = (
            "你是一个专业的技术博客主题增强助手。将用户的简短主题优化为一个"
            "结构化、具体、有深度的博客写作指令。保留核心意图，补充技术细节。"
            "请将增强后的内容包裹在 <enhanced_prompt></enhanced_prompt> 标签中。"
        )

    # 2. 构建消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["prompt"]},
    ]

    # 3. 调用 LLM
    try:
        response = llm_service.chat(messages, caller="prompt_enhancer")
        if not response or not response.strip():
            logger.warning("Empty LLM response, returning original prompt")
            return {"output": state["prompt"]}

        content = response.strip()

        # 4. XML 标签解析（优先）
        xml_match = _XML_PATTERN.search(content)
        if xml_match:
            enhanced = xml_match.group(1).strip()
            logger.info("Extracted enhanced prompt from XML tags")
            return {"output": enhanced}

        # 5. Fallback: 前缀移除
        logger.warning("No XML tags found, using fallback prefix removal")
        for prefix in _PREFIXES_TO_REMOVE:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
                break

        return {"output": content}

    except Exception as e:
        logger.error(f"Prompt enhancement failed: {e}")
        return {"output": state["prompt"]}
