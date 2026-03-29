"""
ThreadChecker Agent - 叙事一致性检查

在 coder_and_artist 之后、reviewer 之前，检查跨章节的叙事连贯性。
检查维度：承诺兑现、叙事流覆盖、核心问题回答、事实一致性、术语一致性、过渡自然度。
"""

import json
import logging
from typing import Dict, Any, List

from ..prompts import get_prompt_manager

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


def _build_document(sections: List[dict]) -> str:
    """将 sections 拼接为完整文档"""
    parts = []
    for section in sections:
        title = section.get('title', '')
        content = section.get('content', '')
        parts.append(f"## {title}\n\n{content}")
    return "\n\n---\n\n".join(parts)


class ThreadCheckerAgent:
    """
    叙事一致性检查 Agent

    检查跨章节的叙事连贯性，输出 reviewer 兼容格式的 issues。
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    def check(self, document: str, outline: Dict[str, Any]) -> Dict[str, Any]:
        """执行叙事一致性检查"""
        pm = get_prompt_manager()

        narrative_mode = outline.get('narrative_mode', 'tutorial')
        logic_chain = []
        narrative_flow = outline.get('narrative_flow', {})
        if narrative_flow:
            logic_chain = narrative_flow.get('logic_chain', [])

        core_questions = []
        for section in outline.get('sections', []):
            cq = section.get('core_question', '')
            if cq:
                core_questions.append({
                    'section_id': section.get('id', ''),
                    'question': cq,
                })

        prompt = pm.render_thread_check(
            document=document,
            narrative_mode=narrative_mode,
            logic_chain=logic_chain,
            core_questions=core_questions,
        )

        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        if not response:
            raise ValueError("LLM 叙事一致性检查返回空响应")
        return _extract_json(response)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行检查并写入 state"""
        if state.get('error'):
            state['thread_issues'] = []
            return state

        sections = state.get('sections', [])
        if len(sections) < 2:
            logger.info("[ThreadChecker] 章节数 < 2，跳过")
            state['thread_issues'] = []
            return state

        outline = state.get('outline', {}) or {}
        document = _build_document(sections)

        try:
            result = self.check(document, outline)
        except Exception as e:
            logger.error(f"[ThreadChecker] 检查异常: {e}")
            state['thread_issues'] = []
            return state

        # 转换为 reviewer 兼容格式
        thread_issues = []
        for issue in result.get('issues', []):
            thread_issues.append({
                'section_id': issue.get('section_id', ''),
                'issue_type': 'narrative_consistency',
                'severity': issue.get('severity', 'medium'),
                'description': f"[叙事一致性-{issue.get('check_type', '')}] {issue.get('description', '')}",
                'suggestion': issue.get('suggestion', ''),
                'check_type': issue.get('check_type', ''),
            })

        state['thread_issues'] = thread_issues
        logger.info(
            f"[ThreadChecker] 完成: coherence={result.get('overall_coherence', 'N/A')}, "
            f"issues={len(thread_issues)}"
        )
        return state
