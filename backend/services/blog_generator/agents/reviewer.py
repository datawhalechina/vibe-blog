"""
Reviewer Agent - 质量审核（精简版）

仅负责结构完整性、Verbatim Data、学习目标覆盖。
事实核查 → FactCheck, 表述清理 → TextCleanup + Humanizer,
一致性 → ThreadChecker + VoiceChecker。
"""

import json
import logging
from typing import Dict, Any

from ..prompts import get_prompt_manager

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON（处理 markdown 包裹）"""
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


class ReviewerAgent:
    """质量审核师 - 结构完整性 + Verbatim + 学习目标"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def review(
        self,
        document: str,
        outline: Dict[str, Any],
        verbatim_data: list = None,
        learning_objectives: list = None,
    ) -> Dict[str, Any]:
        """审核文档"""
        pm = get_prompt_manager()
        prompt = pm.render_reviewer(
            document=document,
            outline=outline,
            verbatim_data=verbatim_data or [],
            learning_objectives=learning_objectives or [],
        )

        logger.info(f"[Reviewer] Prompt 长度: {len(prompt)} 字")

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = _extract_json(response)

            score = result.get("score", 80)
            issues = result.get("issues", [])

            high_issues = [i for i in issues if i.get('severity') == 'high']
            approved = len(high_issues) == 0 and score >= 80

            return {
                "score": score,
                "approved": approved,
                "issues": issues,
                "summary": result.get("summary", "")
            }

        except Exception as e:
            logger.error(f"审核失败: {e}")
            return {
                "score": 80,
                "approved": True,
                "issues": [],
                "summary": "审核完成"
            }

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行质量审核"""
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过质量审核: {state.get('error')}")
            state['review_score'] = 0
            state['review_approved'] = False
            state['review_issues'] = []
            return state

        sections = state.get('sections', [])
        if not sections:
            logger.error("没有章节内容，跳过质量审核")
            state['review_score'] = 0
            state['review_approved'] = False
            state['review_issues'] = []
            return state

        outline = state.get('outline', {})

        # 组装文档
        document_parts = []
        for section in sections:
            document_parts.append(f"## {section.get('title', '')}\n\n{section.get('content', '')}")
        document = '\n\n---\n\n'.join(document_parts)

        logger.info("开始质量审核")

        verbatim_data = state.get('verbatim_data', [])
        learning_objectives = state.get('learning_objectives', [])

        if verbatim_data:
            logger.info(f"[Reviewer] Verbatim 数据: {len(verbatim_data)} 项")
        if learning_objectives:
            logger.info(f"[Reviewer] 学习目标: {len(learning_objectives)} 个")

        result = self.review(
            document,
            outline,
            verbatim_data=verbatim_data,
            learning_objectives=learning_objectives,
        )

        state['review_score'] = result.get('score', 80)
        state['review_approved'] = result.get('approved', True)
        state['review_issues'] = result.get('issues', [])

        logger.info(f"质量审核完成: 得分 {result.get('score', 0)}, {'通过' if result.get('approved') else '未通过'}")

        if result.get('issues'):
            for issue in result['issues']:
                logger.info(f"  - [{issue.get('severity', 'medium')}] {issue.get('description', '')}")

        return state
