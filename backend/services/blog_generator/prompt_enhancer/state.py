"""Prompt 增强器状态定义"""
from typing import Optional, TypedDict, Literal

ArticleStyle = Literal[
    "tutorial", "problem-solution", "comparison",
    "deep-analysis", "narrative", "checklist",
]


class PromptEnhancerState(TypedDict):
    """Prompt 增强器工作流状态"""
    prompt: str                            # 用户原始输入
    context: Optional[str]                 # 附加上下文（如文档摘要）
    article_style: Optional[ArticleStyle]  # 文章风格
    locale: Optional[str]                  # 语言区域 (zh-CN / en-US)
    output: str                            # 增强后的 prompt
