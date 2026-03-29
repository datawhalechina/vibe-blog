"""
VoiceChecker Agent - 语气统一检查

在 coder_and_artist 之后、reviewer 之前，检查全文语气、人称、正式度的一致性。
检查维度：语气一致性、人称一致性、正式度一致性、自称一致性、高频词检测、句式多样性。
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
        sid = section.get('id', '')
        parts.append(f"[{sid}] ## {title}\n\n{content}")
    return "\n\n---\n\n".join(parts)


class VoiceCheckerAgent:
    """
    语气统一检查 Agent

    检查全文语气、人称、正式度的一致性，输出 reviewer 兼容格式的 issues。
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    def check(self, document: str, audience_adaptation: str) -> Dict[str, Any]:
        """执行语气统一检查"""
        pm = get_prompt_manager()

        prompt = pm.render_voice_check(
            document=document,
            audience_adaptation=audience_adaptation,
        )

        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        if not response:
            raise ValueError("LLM 语气统一检查返回空响应")
        return _extract_json(response)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行检查并写入 state"""
        if state.get('error'):
            state['voice_issues'] = []
            return state

        sections = state.get('sections', [])
        if len(sections) < 2:
            logger.info("[VoiceChecker] 章节数 < 2，跳过")
            state['voice_issues'] = []
            return state

        audience = state.get('audience_adaptation', 'default')
        document = _build_document(sections)

        try:
            result = self.check(document, audience)
        except Exception as e:
            logger.error(f"[VoiceChecker] 检查异常: {e}")
            state['voice_issues'] = []
            return state

        # 转换为 reviewer 兼容格式
        voice_issues = []
        for issue in result.get('issues', []):
            voice_issues.append({
                'section_id': issue.get('section_id', ''),
                'issue_type': 'voice_consistency',
                'severity': issue.get('severity', 'low'),
                'description': f"[语气统一-{issue.get('check_type', '')}] {issue.get('description', '')}",
                'suggestion': issue.get('suggestion', ''),
                'check_type': issue.get('check_type', ''),
            })

        state['voice_issues'] = voice_issues
        logger.info(
            f"[VoiceChecker] 完成: issues={len(voice_issues)}, "
            f"summary={result.get('summary', 'N/A')}"
        )
        return state
