"""
Prompt 模板模块 - 从统一的 infrastructure.prompts 导入

模板文件已迁移到 infrastructure/prompts/blog/ 目录下
"""

from infrastructure.prompts import PromptManager, get_prompt_manager

__all__ = [
    'PromptManager',
    'get_prompt_manager',
]
