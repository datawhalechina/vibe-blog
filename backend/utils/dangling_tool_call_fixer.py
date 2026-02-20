"""悬挂工具调用修复 — 适配 VibeBlog LangGraph 工作流"""
from langchain_core.messages import AIMessage, ToolMessage


def fix_dangling_tool_calls(messages: list) -> list:
    """
    扫描消息历史，为缺少 ToolMessage 响应的 tool_calls 注入占位消息。
    适用场景：用户取消、LLM 超时、检查点恢复后消息历史不完整。
    """
    existing_ids = {
        msg.tool_call_id for msg in messages
        if isinstance(msg, ToolMessage)
    }
    patches = []
    for msg in messages:
        if not isinstance(msg, AIMessage) or not getattr(msg, 'tool_calls', None):
            continue
        for tc in msg.tool_calls:
            tc_id = tc.get('id')
            if tc_id and tc_id not in existing_ids:
                patches.append(ToolMessage(
                    content="[工具调用被中断，未返回结果]",
                    tool_call_id=tc_id,
                    name=tc.get('name', 'unknown'),
                    status="error",
                ))
                existing_ids.add(tc_id)
    return patches
