"""
搜索时间窗口工具模块

统一管理 SEARCH_RECENCY_WINDOW 的别名归一化、查询提示追加、
以及各搜索引擎的时间参数映射，避免多处重复实现。
"""
from typing import Optional

# 别名 → 标准值
RECENCY_ALIASES = {
    "1m": "1m",
    "one_month": "1m",
    "1month": "1m",
    "30d": "1m",
    "3m": "3m",
    "three_month": "3m",
    "3month": "3m",
    "90d": "3m",
}


def normalize_recency_window(recency_window: str) -> str:
    """将各种别名归一化为标准值 ('1m' / '3m')，无效值返回空字符串。"""
    if not recency_window:
        return ""
    return RECENCY_ALIASES.get(recency_window.strip().lower(), "")


def normalize_recency_window_optional(recency_window: str) -> Optional[str]:
    """同 normalize_recency_window，但无效值返回 None（供 Serper 使用）。"""
    if not recency_window:
        return None
    return RECENCY_ALIASES.get(recency_window.strip().lower())


def apply_recency_hint(query: str, recency_window: str) -> str:
    """在查询词后追加时间提示（中英文自动判断），已存在则跳过。"""
    if not query or not recency_window:
        return query
    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in query)
    if recency_window == "1m":
        hint = "最近1个月" if has_chinese else "last 1 month"
        return query if hint in query else f"{query} {hint}"
    if recency_window == "3m":
        hint = "最近3个月" if has_chinese else "last 3 months"
        return query if hint in query else f"{query} {hint}"
    return query


def to_serper_tbs(recency_window: str) -> Optional[str]:
    """将标准时间窗口映射为 Serper tbs 参数值。"""
    if recency_window == "1m":
        return "qdr:m"
    if recency_window == "3m":
        return "qdr:m3"
    return None


def to_zai_recency_filter(recency_window: str) -> str:
    """将标准时间窗口映射为智谱 search_recency_filter 值。"""
    if recency_window == "1m":
        return "oneMonth"
    # 智谱当前常见取值不包含 3 个月，3m 通过 query hint 约束
    return ""
