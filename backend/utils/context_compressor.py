"""
上下文压缩策略

多级上下文管理：工具结果选择性保留 → 搜索素材裁剪 → 修订历史压缩。
与 37.33 ContextGuard 配合，确保不超限。

来源：37.06 上下文压缩策略迁移方案
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    上下文压缩器 — 为不同 Agent 场景提供定制化的上下文压缩

    降级策略（按 usage_ratio）：
      < 70%  → 不压缩
      70-85% → 省略旧工具结果
      85-95% → 省略旧工具结果 + 裁剪搜索素材
      > 95%  → 交给 37.33 ContextGuard 兜底
    """

    def __init__(self, model_name: str = 'gpt-4o', llm_service=None):
        self.model_name = model_name
        self.llm = llm_service

    # ============ 核心方法 ============

    def filter_tool_results(
        self, messages: List[Dict], keep_recent: int = 5,
    ) -> List[Dict]:
        """
        选择性替换旧工具结果为占位文本。

        规则：
        1. 始终保留第一条用户消息
        2. 保留所有 assistant 消息
        3. 只保留最近 K 个 tool 结果的完整内容
        4. 更早的 tool 结果替换为占位文本（而非删除）
        """
        if keep_recent == -1:
            return messages

        tool_indices = [
            i for i, m in enumerate(messages)
            if m.get('role') == 'tool' and i > 0
        ]

        if keep_recent == 0:
            to_replace = tool_indices
        elif len(tool_indices) > keep_recent:
            to_replace = tool_indices[:-keep_recent]
        else:
            to_replace = []

        for idx in to_replace:
            messages[idx] = {**messages[idx], 'content': 'Tool result is omitted to save tokens.'}

        return messages

    def apply_strategy(
        self, messages: List[Dict], usage_ratio: float,
    ) -> List[Dict]:
        """
        根据上下文使用率选择压缩策略。

        < 70%  → 不压缩
        70-85% → 省略旧工具结果（keep_recent=3）
        85-95% → 省略旧工具结果（keep_recent=1）+ 裁剪长内容
        > 95%  → 交给 ContextGuard 兜底（此处仍做最大努力压缩）
        """
        if usage_ratio < 0.70:
            return messages

        if usage_ratio < 0.85:
            return self.filter_tool_results(messages, keep_recent=3)

        # 85%+ : 激进压缩
        messages = self.filter_tool_results(messages, keep_recent=1)
        # 裁剪过长的单条消息内容
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str) and len(content) > 3000 and msg.get('role') != 'system':
                msg['content'] = content[:2000] + '\n\n... [内容已裁剪以适应上下文窗口] ...'

        return messages

    # ============ 搜索结果压缩 ============

    def compress_search_results(
        self, results: List[Dict],
        max_results: int = 10,
        max_chars_per_result: int = 500,
    ) -> List[Dict]:
        """压缩搜索结果：去重 + 截断 + 限数"""
        seen_urls = set()
        compressed = []
        for result in results[:max_results * 2]:
            url = result.get('url', result.get('link', ''))
            if url in seen_urls:
                continue
            seen_urls.add(url)
            compressed.append({
                'title': result.get('title', '')[:200],
                'url': url,
                'snippet': result.get('snippet', result.get('content', ''))[:max_chars_per_result],
                'source': result.get('source', ''),
            })
            if len(compressed) >= max_results:
                break
        return compressed

    # ============ 修订历史压缩 ============

    def compress_revision_history(
        self, history: List[Dict], keep_last_n: int = 2,
    ) -> List[Dict]:
        """保留最近 N 轮完整记录，更早的只保留摘要"""
        if len(history) <= keep_last_n:
            return history
        compressed = []
        for h in history[:-keep_last_n]:
            compressed.append({
                'round': h.get('round', 0),
                'summary': h.get('summary', ''),
                'score': h.get('score', 0),
                'issues_count': len(h.get('issues', [])),
            })
        compressed.extend(history[-keep_last_n:])
        return compressed

    # ============ Agent 场景压缩 ============

    def compress_for_writer(self, state: Dict[str, Any], section_index: int) -> Dict:
        """为 Writer 压缩上下文"""
        outline = state.get('outline', {})
        sections = outline.get('sections', [])
        search_results = state.get('search_results', [])
        current = sections[section_index] if section_index < len(sections) else {}
        return {
            'outline_summary': self._compress_outline(outline),
            'current_section': current,
            'previous_summary': self._get_section_summary(sections, section_index - 1),
            'next_preview': self._get_section_preview(sections, section_index + 1),
            'relevant_search': self._filter_relevant_search(search_results, current),
        }

    def compress_for_reviewer(self, state: Dict[str, Any]) -> Dict:
        """为 Reviewer 压缩上下文"""
        return {
            'outline': state.get('outline', {}),
            'full_text_summary': self._generate_full_text_summary(state.get('sections', [])),
            'sections': state.get('sections', []),
            'last_review_summary': self._compress_review_history(state.get('review_history', [])),
        }

    # ============ 内部方法 ============

    def _compress_outline(self, outline: Dict) -> str:
        sections = outline.get('sections', [])
        lines = [f"主题: {outline.get('topic', '')}"]
        for i, s in enumerate(sections):
            lines.append(f"{i+1}. {s.get('title', '')} — {s.get('core_question', '')}")
        return '\n'.join(lines)

    def _get_section_summary(self, sections: List[Dict], index: int) -> str:
        if index < 0 or index >= len(sections):
            return ""
        s = sections[index]
        content = s.get('content', '')
        if not content:
            return f"[{s.get('title', '')}] 尚未撰写"
        return f"[{s.get('title', '')}] {content[:300]}..."

    def _get_section_preview(self, sections: List[Dict], index: int) -> str:
        if index < 0 or index >= len(sections):
            return ""
        s = sections[index]
        return f"[下一章: {s.get('title', '')}] 核心问题: {s.get('core_question', '')}"

    def _filter_relevant_search(self, results: List[Dict], section: Dict) -> List[Dict]:
        keywords = section.get('keywords', [])
        title = section.get('title', '').lower()
        if not keywords and not title:
            return results[:5]
        scored = []
        for r in results:
            score = 0
            text = (r.get('title', '') + ' ' + r.get('snippet', r.get('content', ''))).lower()
            for kw in keywords:
                if kw.lower() in text:
                    score += 1
            if title and any(w in text for w in title.split() if len(w) > 1):
                score += 1
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:5]]

    def _generate_full_text_summary(self, sections: List[Dict]) -> str:
        parts = []
        for s in sections:
            content = s.get('content', '')
            if content:
                parts.append(f"## {s.get('title', '')}\n{content[:200]}...")
        return '\n\n'.join(parts)

    def _compress_review_history(self, history: List[Dict]) -> str:
        if not history:
            return "无历史审核记录"
        last = history[-1]
        issues = last.get('issues', [])
        return f"上轮审核: 分数 {last.get('score', 'N/A')}, {len(issues)} 个问题"
