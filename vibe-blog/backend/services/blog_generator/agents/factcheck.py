"""
FactCheck Agent - 事实核查

从全文提取可验证 Claim，与 Researcher 搜索结果交叉验证。
位于 reviewer/revision 之后、humanizer 之前。
"""

import json
import logging
import os
from typing import Dict, Any, List

from ..prompts import get_prompt_manager

logger = logging.getLogger(__name__)

VERDICT_MAP = {"S": "SUPPORTED", "C": "CONTRADICTED", "U": "UNVERIFIED"}


def _extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


def _build_content(sections: List[dict]) -> str:
    """拼接全部章节内容"""
    parts = []
    for s in sections:
        sid = s.get('id', '')
        title = s.get('title', '')
        content = s.get('content', '')
        parts.append(f"[{sid}] {title}: {content}")
    return "\n".join(parts)


def _build_evidence(search_results: List[dict]) -> str:
    """拼接证据源（搜索结果）"""
    if not search_results:
        return "(无证据)"
    parts = []
    for i, sr in enumerate(search_results):
        title = sr.get('title', '')
        content = sr.get('content', '')[:300]
        parts.append(f"[S{i+1}] {title}: {content}")
    return "\n".join(parts)


def _normalize_report(raw: dict) -> dict:
    """将紧凑格式转换为标准报告格式"""
    claims = []
    supported = contradicted = unverified = 0
    for c in raw.get('claims', []):
        v_short = c.get('v', 'U')
        verdict = VERDICT_MAP.get(v_short, v_short)
        if verdict == 'SUPPORTED':
            supported += 1
        elif verdict == 'CONTRADICTED':
            contradicted += 1
        else:
            unverified += 1
        claims.append({
            'id': c.get('id', 0),
            'claim': c.get('text', ''),
            'section_id': c.get('sid', ''),
            'verdict': verdict,
        })

    fixes = []
    for f in raw.get('fixes', []):
        fixes.append({
            'section_id': f.get('sid', ''),
            'action': 'replace',
            'original': f.get('old', ''),
            'replacement': f.get('new', ''),
        })

    return {
        'overall_score': raw.get('score', 5),
        'total_claims': len(claims),
        'supported': supported,
        'contradicted': contradicted,
        'unverified': unverified,
        'claims': claims,
        'fix_instructions': fixes,
    }

class FactCheckAgent:
    """
    事实核查 Agent

    从全文提取可验证 Claim，与搜索结果交叉验证，
    自动修复 CONTRADICTED Claim，标记 UNVERIFIED Claim。
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.skip_threshold = int(os.getenv('FACTCHECK_SKIP_THRESHOLD', '4'))
        self.auto_fix = os.getenv('FACTCHECK_AUTO_FIX', 'true').lower() == 'true'

    def check(self, all_content: str, all_evidence: str) -> Dict[str, Any]:
        """执行事实核查"""
        pm = get_prompt_manager()
        prompt = pm.render_factcheck(
            all_content=all_content,
            all_evidence=all_evidence,
        )
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        if not response or not response.strip():
            raise ValueError("LLM 事实核查返回空响应")
        raw = _extract_json(response)
        return _normalize_report(raw)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行事实核查并写入 state"""
        if state.get('error'):
            return state

        sections = state.get('sections', [])
        if not sections:
            return state

        search_results = state.get('search_results', [])
        all_content = _build_content(sections)
        all_evidence = _build_evidence(search_results)

        try:
            report = self.check(all_content, all_evidence)
        except Exception as e:
            logger.error(f"[FactCheck] 核查异常: {e}")
            state['factcheck_report'] = {'error': str(e)}
            return state

        state['factcheck_report'] = report
        overall_score = report.get('overall_score', 5)

        logger.info(
            f"[FactCheck] 完成: 评分 {overall_score}/5, "
            f"Claim {report.get('total_claims', 0)} 条 "
            f"(支持 {report.get('supported', 0)}, "
            f"矛盾 {report.get('contradicted', 0)}, "
            f"未验证 {report.get('unverified', 0)})"
        )

        if overall_score >= self.skip_threshold:
            logger.info(f"[FactCheck] 评分 {overall_score} >= {self.skip_threshold}，跳过修复")
            return state

        if not self.auto_fix:
            logger.info("[FactCheck] 自动修复已禁用")
            return state

        # 自动修复
        section_map = {s.get('id', ''): s for s in sections}
        fix_count = 0
        for fix in report.get('fix_instructions', []):
            sid = fix.get('section_id', '')
            section = section_map.get(sid)
            if not section:
                continue
            original = fix.get('original', '')
            if not original or original not in section.get('content', ''):
                continue
            replacement = fix.get('replacement', '')
            if replacement:
                section['content'] = section['content'].replace(
                    original, replacement
                )
                fix_count += 1

        if fix_count:
            logger.info(f"[FactCheck] 自动修复 {fix_count} 处")

        return state
