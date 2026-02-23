"""
引用合并 — URL 精确去重，高分覆盖低分
用于 LangGraph 并行节点写入 citation_collection 时的 reducer
"""
from typing import Any, Dict, List


def merge_citations(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """URL 精确去重合并，高分覆盖低分，保持插入顺序"""
    if not existing and not new:
        return []

    seen: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for c in (existing or []):
        url = c.get("url", "")
        if not url:
            continue
        seen[url] = c
        order.append(url)

    for c in (new or []):
        url = c.get("url", "")
        if not url:
            continue
        if url not in seen:
            seen[url] = c
            order.append(url)
        elif c.get("credibility_score", 0) > seen[url].get("credibility_score", 0):
            seen[url] = c

    return [seen[url] for url in order]
