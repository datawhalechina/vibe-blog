"""
自定义状态 Reducer（102.10 迁移特性 B）

解决 LangGraph 并行节点写入同一字段时的数据丢失问题。
提供 merge_list_dedup 和 merge_sections 两个 reducer 函数，
以及 STATE_REDUCERS 注册表供管道使用。

环境变量开关：STATE_REDUCERS_ENABLED (default: true)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List


def merge_list_dedup(existing: List[Any], new: List[Any]) -> List[Any]:
    """
    去重合并两个列表，保持顺序（existing 优先）。
    字典项按 str() 去重。
    """
    if not new:
        return list(existing) if existing else []
    if not existing:
        return list(new)

    seen = set()
    result = []
    for item in existing:
        key = str(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    for item in new:
        key = str(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def merge_sections(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    按 id 字段合并 sections 列表。
    同 id 的 section 用 new 覆盖 existing，新 id 追加到末尾。
    """
    if not new:
        return list(existing) if existing else []
    if not existing:
        return list(new)

    result_map: Dict[str, Dict] = {}
    order: List[str] = []

    for s in existing:
        sid = s.get("id", str(id(s)))
        result_map[sid] = s
        order.append(sid)

    for s in new:
        sid = s.get("id", str(id(s)))
        result_map[sid] = s
        if sid not in order:
            order.append(sid)

    return [result_map[sid] for sid in order]


# 注册表：字段名 → reducer 函数
STATE_REDUCERS: Dict[str, Callable[[List, List], List]] = {
    "search_results": merge_list_dedup,
    "sections": merge_sections,
    "images": merge_list_dedup,
    "code_blocks": merge_list_dedup,
    "section_images": merge_list_dedup,
    "key_concepts": merge_list_dedup,
    "reference_links": merge_list_dedup,
    "review_issues": merge_list_dedup,
}
