"""
41.18 工具增强 LLM — 让 LLM 在推理中自主调用搜索工具

在现有 chat() 基础上增加 chat_with_tools()：
1. 绑定工具定义到 LLM 调用
2. LLM 自主决定是否调用工具
3. 执行工具调用并将结果回注
4. 继续推理直到 LLM 给出最终回答

环境变量：
- LLM_TOOLS_ENABLED: 是否启用（默认 false）
- LLM_TOOLS_MAX_ROUNDS: 最大工具调用轮数（默认 3）
"""
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolDefinition:
    """工具定义"""

    def __init__(self, name: str, description: str,
                 parameters: Dict[str, Any], handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_openai_schema(self) -> Dict:
        """转换为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class ToolFactory:
    """工具工厂 — 创建可用工具集"""

    @staticmethod
    def create_search_tool(search_service) -> Optional[ToolDefinition]:
        """创建搜索工具"""
        if not search_service:
            return None

        def search_handler(query: str, max_results: int = 5) -> str:
            try:
                result = search_service.search(query, max_results=max_results)
                if result.get('success') and result.get('results'):
                    items = result['results'][:max_results]
                    return json.dumps([
                        {"title": r.get("title", ""), "url": r.get("url", ""),
                         "snippet": (r.get("content", "") or r.get("snippet", ""))[:200]}
                        for r in items
                    ], ensure_ascii=False)
                return "[]"
            except Exception as e:
                return f"搜索失败: {e}"

        return ToolDefinition(
            name="web_search",
            description="搜索互联网获取最新信息。当需要查找事实、数据、最新动态时使用。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "max_results": {"type": "integer", "description": "最大结果数", "default": 5},
                },
                "required": ["query"],
            },
            handler=search_handler,
        )


class ToolEnhancedLLM:
    """工具增强 LLM 包装器"""

    def __init__(self, llm_client, tools: List[ToolDefinition] = None):
        self.llm = llm_client
        self.tools = tools or []
        self.max_rounds = int(os.environ.get('LLM_TOOLS_MAX_ROUNDS', '3'))
        self._tool_map = {t.name: t for t in self.tools}

    def chat_with_tools(self, messages: List[Dict], **kwargs) -> str:
        """
        带工具调用的 chat。

        LLM 可以在推理过程中自主决定是否调用工具。
        工具调用结果会自动回注到对话中。

        Returns:
            最终文本回答
        """
        if not self.tools:
            return self.llm.chat(messages=messages, **kwargs)

        tool_schemas = [t.to_openai_schema() for t in self.tools]
        current_messages = list(messages)

        for round_num in range(self.max_rounds):
            # 调用 LLM（带工具定义）
            try:
                response = self.llm.chat(
                    messages=current_messages,
                    tools=tool_schemas,
                    **kwargs,
                )
            except TypeError:
                # 如果 chat() 不支持 tools 参数，回退到普通调用
                logger.info("[ToolEnhancedLLM] LLM 不支持 tools 参数，回退到普通调用")
                return self.llm.chat(messages=current_messages, **kwargs)

            # 检查是否有工具调用
            if isinstance(response, str):
                return response  # 纯文本回答，直接返回

            # 处理工具调用（假设返回结构化响应）
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_calls = response.tool_calls
            elif isinstance(response, dict) and response.get('tool_calls'):
                tool_calls = response['tool_calls']

            if not tool_calls:
                # 没有工具调用，提取文本内容
                if hasattr(response, 'content'):
                    return response.content or ""
                if isinstance(response, dict):
                    return response.get('content', str(response))
                return str(response)

            # 执行工具调用
            for tc in tool_calls:
                func_name = tc.get('function', {}).get('name', '') if isinstance(tc, dict) else getattr(tc.function, 'name', '')
                func_args_str = tc.get('function', {}).get('arguments', '{}') if isinstance(tc, dict) else getattr(tc.function, 'arguments', '{}')
                tc_id = tc.get('id', '') if isinstance(tc, dict) else getattr(tc, 'id', '')

                tool = self._tool_map.get(func_name)
                if not tool:
                    logger.warning(f"[ToolEnhancedLLM] 未知工具: {func_name}")
                    continue

                try:
                    args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
                    result = tool.handler(**args)
                    logger.info(f"[ToolEnhancedLLM] 工具调用: {func_name}({args}) → {len(str(result))} 字符")
                except Exception as e:
                    result = f"工具调用失败: {e}"
                    logger.warning(f"[ToolEnhancedLLM] {func_name} 执行失败: {e}")

                # 回注工具结果
                current_messages.append({
                    "role": "assistant",
                    "tool_calls": [tc] if isinstance(tc, dict) else [{"id": tc_id, "function": {"name": func_name, "arguments": func_args_str}, "type": "function"}],
                })
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": str(result),
                })

        # 达到最大轮数，做最后一次普通调用
        return self.llm.chat(messages=current_messages, **kwargs)
