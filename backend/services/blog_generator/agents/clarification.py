"""
ClarificationAgent — 主动澄清机制

分析用户输入的 topic 和参数，判断是否需要在生成前向用户澄清。
5 种澄清类型：missing_info, ambiguous_requirement, approach_choice,
risk_confirmation, suggestion。

环境变量开关：CLARIFICATION_ENABLED (default: true)
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 澄清类型定义
CLARIFICATION_TYPES = [
    "missing_info",
    "ambiguous_requirement",
    "approach_choice",
    "risk_confirmation",
    "suggestion",
]

# 类型 → 图标映射
CLARIFICATION_ICONS = {
    "missing_info": "❓",
    "ambiguous_requirement": "🤔",
    "approach_choice": "🔀",
    "risk_confirmation": "⚠️",
    "suggestion": "💡",
}

MAX_CLARIFICATION_ROUNDS = 2

CLARIFICATION_PROMPT = """你是一个博客生成前的需求澄清助手。分析用户的博客生成请求，判断是否需要在开始生成前向用户提问。

## 用户请求
- 主题: {topic}
- 文章类型: {article_type}
- 目标受众: {target_audience}
- 目标长度: {target_length}
- 参考资料: {source_material}
## 澄清场景（必须检查）

1. **missing_info**: 主题过于宽泛（少于 5 个字且无明确技术栈），缺少关键上下文
2. **ambiguous_requirement**: 主题可以有多种完全不同的解读方向
3. **approach_choice**: 同一主题有多种写作角度（入门教程 vs 深度原理 vs 实战对比）
4. **risk_confirmation**: 长文生成（long/deep）预计耗时超过 10 分钟，需确认
5. **suggestion**: 你有更好的主题建议（更具体、更有价值）

## 判断规则
- 如果主题明确、参数完整、无歧义 → 不需要澄清
- 如果主题少于 5 字且无技术关键词 → 需要 missing_info 澄清
- 如果主题可解读为 2+ 种完全不同的方向 → 需要 ambiguous_requirement
- 如果 target_length 为 long/deep 且无 source_material → 建议 risk_confirmation

## 输出格式（JSON）
{{
  "needs_clarification": true/false,
  "questions": [
    {{
      "question": "具体问题",
      "clarification_type": "missing_info",
      "context": "为什么需要这个信息",
      "options": ["选项1", "选项2"]
    }}
  ]
}}

如果不需要澄清，questions 为空数组。最多提 2 个问题。
"""


def format_clarification_message(
    question: str,
    clarification_type: str,
    context: Optional[str] = None,
    options: Optional[List[str]] = None,
) -> str:
    """格式化澄清消息，带图标和选项列表"""
    icon = CLARIFICATION_ICONS.get(clarification_type, "❓")
    parts = [f"{icon} {question}"]
    if context:
        parts.append(f"\n> {context}")
    if options:
        parts.append("")
        for i, opt in enumerate(options, 1):
            parts.append(f"{i}. {opt}")
    return "\n".join(parts)


class ClarificationAgent:
    """主动澄清 Agent — 在博客生成前分析用户意图"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析用户请求，判断是否需要澄清。

        Returns:
            {"clarification_needed": bool, "clarification_questions": list}
        """
        # 环境变量开关
        if os.getenv("CLARIFICATION_ENABLED", "true").lower() == "false":
            return {"clarification_needed": False, "clarification_questions": []}

        # 澄清轮数限制
        if state.get("clarification_round", 0) >= MAX_CLARIFICATION_ROUNDS:
            return {"clarification_needed": False, "clarification_questions": []}

        topic = state.get("topic", "")
        article_type = state.get("article_type", "tutorial")
        target_audience = state.get("target_audience", "intermediate")
        target_length = state.get("target_length", "medium")
        source_material = state.get("source_material", "")

        prompt = CLARIFICATION_PROMPT.format(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material or "无",
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            if not response or not response.strip():
                return {"clarification_needed": False, "clarification_questions": []}

            result = json.loads(response)
            needs = result.get("needs_clarification", False)
            questions = result.get("questions", [])

            # 校验 clarification_type
            for q in questions:
                if q.get("clarification_type") not in CLARIFICATION_TYPES:
                    q["clarification_type"] = "missing_info"

            return {
                "clarification_needed": needs and len(questions) > 0,
                "clarification_questions": questions[:2],
            }

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"澄清分析失败，跳过澄清: {e}")
            return {"clarification_needed": False, "clarification_questions": []}
