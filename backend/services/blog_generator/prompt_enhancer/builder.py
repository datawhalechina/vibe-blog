"""Prompt 增强器 LangGraph 子图构建"""
from functools import partial

from langgraph.graph import StateGraph

from .state import PromptEnhancerState


def build_prompt_enhancer_graph(llm_service):
    """构建 Prompt 增强器子图"""
    from .enhancer_node import prompt_enhancer_node

    node_fn = partial(prompt_enhancer_node, llm_service=llm_service)

    builder = StateGraph(PromptEnhancerState)
    builder.add_node("enhancer", node_fn)
    builder.set_entry_point("enhancer")
    builder.set_finish_point("enhancer")
    return builder.compile()
