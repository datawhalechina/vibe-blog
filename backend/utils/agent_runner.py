"""
AgentRunner — 统一 Agent 执行器

封装 LLM 调用的通用逻辑：
  - JSON 响应提取（处理 markdown 包裹）
  - 自动重试（可配置次数）
  - 统一日志
  - Token 追踪（预留接口）

用法：
    runner = AgentRunner(llm_client)
    result = runner.chat_json(messages, max_retries=2)
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = int(os.getenv('AGENT_RUNNER_MAX_RETRIES', '2'))


def extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON（处理 markdown 包裹）"""
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


class AgentRunner:
    """统一 Agent 执行器"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def chat(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """执行 LLM 调用，返回原始文本"""
        return self.llm.chat(messages=messages, response_format=response_format)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        max_retries: int = DEFAULT_MAX_RETRIES,
        caller: str = "",
    ) -> Dict[str, Any]:
        """
        执行 LLM 调用并解析 JSON 响应。

        自动处理 markdown 包裹，失败时重试。

        Args:
            messages: 消息列表
            max_retries: 最大重试次数（不含首次）
            caller: 调用方标识（用于日志）

        Returns:
            解析后的 dict
        """
        label = f"[{caller}] " if caller else ""
        last_error = None

        for attempt in range(1 + max_retries):
            try:
                response = self.llm.chat(
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                if not response or not response.strip():
                    raise ValueError("LLM 返回空响应")
                return extract_json(response)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"{label}JSON 解析失败 (尝试 {attempt + 1}/{1 + max_retries}): {e}"
                    )
                else:
                    logger.error(f"{label}JSON 解析最终失败: {e}")

        raise last_error  # type: ignore[misc]
