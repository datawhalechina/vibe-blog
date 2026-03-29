"""
41.11 Guidelines 驱动审核 — 预设审核标准库

按博客类型提供不同的审核标准列表，注入到 Reviewer Prompt 中。
"""

from typing import Dict, List

TECH_TUTORIAL_GUIDELINES: List[str] = [
    "代码示例必须可运行，包含必要的 import 和上下文",
    "技术术语首次出现时需要解释",
    "步骤说明必须有明确的前置条件和预期结果",
    "版本号和 API 必须标注适用版本",
]

SCIENCE_POPULAR_GUIDELINES: List[str] = [
    "专业概念必须用类比或日常例子解释",
    "避免未经解释的公式和符号",
    "数据引用必须标注来源",
    "结论不能过度简化或误导",
]

DEEP_ANALYSIS_GUIDELINES: List[str] = [
    "论点必须有数据或案例支撑",
    "需要呈现正反两面观点",
    "引用来源必须权威且可追溯",
    "分析深度需超越表面描述，揭示底层逻辑",
]

GUIDELINES_BY_TYPE: Dict[str, List[str]] = {
    'tutorial': TECH_TUTORIAL_GUIDELINES,
    'tech_tutorial': TECH_TUTORIAL_GUIDELINES,
    'science_popular': SCIENCE_POPULAR_GUIDELINES,
    'deep_analysis': DEEP_ANALYSIS_GUIDELINES,
}


def get_guidelines(article_type: str) -> List[str]:
    """按文章类型获取审核标准"""
    return GUIDELINES_BY_TYPE.get(article_type, [])
