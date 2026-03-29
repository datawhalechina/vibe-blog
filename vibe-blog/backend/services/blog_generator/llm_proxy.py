"""
41.06 三级 LLM 模型策略 — TieredLLMProxy

对 Agent 完全透明的 LLMService 代理，自动注入 tier 参数。
Agent 代码零改动，self.llm.chat() 调用自动路由到对应级别模型。
"""

import logging

logger = logging.getLogger(__name__)


class TieredLLMProxy:
    """LLMService 的 tier 代理。

    覆盖 chat() / chat_stream() / chat_with_image() 三个公开方法，
    注入 tier 参数实现模型路由。其余属性透传到底层 LLMService。
    """

    def __init__(self, llm_service, tier: str):
        self._llm = llm_service
        self._tier = tier

    def chat(self, messages, *, thinking=False, thinking_budget=19000, **kwargs):
        """注入 tier 的 chat 调用，透传 thinking 参数。"""
        return self._llm.chat(
            messages, tier=self._tier,
            thinking=thinking, thinking_budget=thinking_budget,
            **kwargs,
        )

    def chat_stream(self, messages, *, temperature=0.7, on_chunk=None,
                    response_format=None, caller="", **kwargs):
        """注入 tier 的流式调用。"""
        return self._llm.chat_stream(
            messages, tier=self._tier,
            temperature=temperature, on_chunk=on_chunk,
            response_format=response_format, caller=caller,
            **kwargs,
        )

    def chat_with_image(self, prompt, image_base64, mime_type="image/jpeg", **kwargs):
        """多模态调用，固定使用 smart 级别（图片理解需要较强模型）。"""
        return self._llm.chat_with_image(
            prompt, image_base64, mime_type,
            tier='smart',
            **kwargs,
        )

    def __getattr__(self, name):
        """其余属性透传到底层 LLMService。"""
        return getattr(self._llm, name)
