"""
插图类型自动推荐模块 - 基于内容信号的 Type 推荐

根据章节内容中的关键词和模式，自动推荐最合适的插图类型（illustration_type）。
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 内容信号定义：每种 Type 对应的关键词和正则模式
# keywords 匹配权重 = 1，patterns 匹配权重 = 2
TYPE_SIGNALS = {
    "flowchart": {
        "keywords": [
            "步骤", "流程", "pipeline", "workflow", "工作流",
            "先", "再", "然后", "接着", "最后",
            "第一步", "第二步", "第三步",
            "阶段", "phase", "stage", "step",
            "执行顺序", "处理流程", "操作步骤",
        ],
        "patterns": [
            r"步骤\s*\d+",
            r"Phase\s*\d+",
            r"Step\s*\d+",
            r"→.*→",
            r"->.*->",
            r"第[一二三四五六七八九十]+步",
        ],
    },
    "comparison": {
        "keywords": [
            "对比", "比较", "vs", "versus", "区别", "差异",
            "优缺点", "优劣", "相比", "不同", "异同",
            "优势", "劣势", "pros", "cons",
            "选择", "哪个更好", "对照",
        ],
        "patterns": [
            r"\bvs\.?\b",
            r"A\s*[与和]\s*B",
            r"方案[一二1-9]\s*[与和vs]",
            r"(.+)\s+vs\.?\s+(.+)",
        ],
    },
    "framework": {
        "keywords": [
            "架构", "模型", "层", "组件", "模块",
            "系统设计", "分层", "architecture", "framework",
            "层级", "结构", "拓扑", "topology",
            "微服务", "中间件", "基础设施",
            "接口", "API", "服务层", "数据层",
        ],
        "patterns": [
            r".*层.*层",
            r"架构图",
            r"系统架构",
            r"[三四五六七]层",
            r"(表现|业务|数据|基础设施)层",
        ],
    },
    "timeline": {
        "keywords": [
            "历史", "演进", "版本", "发展", "路线图",
            "里程碑", "milestone", "roadmap",
            "变迁", "演变", "迭代", "进化",
            "从...到...", "早期", "后来",
        ],
        "patterns": [
            r"\d{4}\s*年",
            r"v\d+\.\d+",
            r"(19|20)\d{2}",
            r"第[一二三四五]代",
        ],
    },
    "infographic": {
        "keywords": [
            "数据", "指标", "统计", "百分比", "排名",
            "概览", "总结", "概述", "一览",
            "关键数字", "核心指标", "KPI",
            "分布", "占比", "增长率",
        ],
        "patterns": [
            r"\d+%",
            r"\d+\s*(个|项|种|条|张|篇)",
            r"(增长|下降|提升)\s*\d+",
            r"Top\s*\d+",
        ],
    },
    "scene": {
        "keywords": [
            "想象", "场景", "故事", "案例", "实际",
            "日常", "情景", "画面", "体验",
            "用户", "开发者", "工程师",
            "一天", "某天", "有一次",
        ],
        "patterns": [
            r"想象一下",
            r"假设你",
            r"比如说",
        ],
    },
}

# 默认类型（当所有信号得分都为 0 时使用）
DEFAULT_TYPE = "infographic"


def auto_recommend_type(content: str) -> str:
    """
    根据内容信号自动推荐插图类型

    Args:
        content: 章节内容文本

    Returns:
        推荐的 illustration_type ID
    """
    if not content or not content.strip():
        return DEFAULT_TYPE

    content_lower = content.lower()
    scores = {}

    for type_id, signals in TYPE_SIGNALS.items():
        score = 0

        # 关键词匹配（权重 1）
        for keyword in signals.get("keywords", []):
            if keyword.lower() in content_lower:
                score += 1

        # 正则模式匹配（权重 2）
        for pattern in signals.get("patterns", []):
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    score += 2
            except re.error:
                continue

        scores[type_id] = score

    # 所有得分为 0 时返回默认类型
    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return DEFAULT_TYPE

    recommended = max(scores, key=scores.get)
    logger.debug(f"Type 自动推荐: {recommended} (得分: {scores})")
    return recommended


def get_type_signals() -> dict:
    """获取所有类型信号定义（用于调试和测试）"""
    return TYPE_SIGNALS.copy()
