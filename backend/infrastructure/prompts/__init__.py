"""
统一 Prompt 模板管理模块

所有 Prompt 模板统一存放在 infrastructure/prompts/ 下的子目录中:
- blog/          博客生成 Agent 模板
- reviewer/      内容评审模板
- image_styles/  图片风格模板
- shared/        共享模板（文档解析等）
"""

from .prompt_manager import PromptManager, get_prompt_manager

__all__ = [
    'PromptManager',
    'get_prompt_manager',
]
