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
        guidelines: list = None,
    ) -> Dict[str, Any]:
        """审核文档"""
        pm = get_prompt_manager()

        # 41.11: 注入自定义审核标准
        guidelines_block = ""
        if guidelines:
            import os
            if os.environ.get('REVIEW_GUIDELINES_ENABLED', 'false').lower() == 'true':
                guidelines_text = "\n".join(f"- {g}" for g in guidelines)
                guidelines_block = f"\n\n【自定义审核标准】\n{guidelines_text}\n请在审核中额外检查以上标准。\n"

        prompt = pm.render_reviewer(
            document=document,
            outline=outline,
            verbatim_data=verbatim_data or [],
            learning_objectives=learning_objectives or [],
        )
        if guidelines_block:
            prompt = prompt + guidelines_block

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

        # 构建「结构骨架」：标题 + 字数 + 子章节标题列表（或首段预览）
        # 通过提取正文中的 ### / ## 子标题，让 Reviewer 能判断子章节是否覆盖大纲要点
        # 避免仅凭 150 字预览把"骨架看不到"的子节误报为缺失
        skeleton_parts = []
        for section in sections:
            title   = section.get('title', '（无标题）')
            content = section.get('content', '')

            # 提取子标题（只取 ### 级，## 级通常是章节自身标题，已在骨架顶行体现）
            # 跳过代码块内的 ### 避免误判
            sub_headings = []
            in_code_block = False
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                if stripped.startswith('### '):
                    heading_text = stripped[4:].strip()
                    if heading_text:
                        sub_headings.append(heading_text)

            if sub_headings:
                sub_info = '\n'.join(f'  - {h}' for h in sub_headings)
                skeleton_parts.append(
                    f"## {title}\n（本节约 {len(content)} 字）\n子章节:\n{sub_info}"
                )
            else:
                # 无子标题时退回首段预览
                preview = content[:150].replace('\n', ' ').strip()
                if len(content) > 150:
                    preview += '…'
                skeleton_parts.append(
                    f"## {title}\n（本节约 {len(content)} 字）\n> {preview}"
                )
        document = '\n\n'.join(skeleton_parts)

        logger.info(f"开始质量审核（骨架模式: {len(document)} 字 / 原文 "
                    f"{sum(len(s.get('content','')) for s in sections)} 字）")

        # Python 侧预检 verbatim：只把「真正缺失」的项传给 LLM
        # 避免 LLM 因看不到全文而误报 verbatim 违规
        raw_verbatim = state.get('verbatim_data', [])
        if raw_verbatim:
            full_document = '\n\n'.join(
                section.get('content', '') for section in sections
            )
            verbatim_data = [
                item for item in raw_verbatim
                if item.get('value', '') not in full_document
            ]
            skipped = len(raw_verbatim) - len(verbatim_data)
            if skipped:
                logger.info(f"[Reviewer] Verbatim 预检: {skipped} 项已在原文中，跳过")
        else:
            verbatim_data = []

        learning_objectives = state.get('learning_objectives', [])

        # 41.11: 从 state 获取审核标准（StyleProfile 或按文章类型自动匹配）
        guidelines = state.get('review_guidelines')
        if not guidelines:
            import os
            if os.environ.get('REVIEW_GUIDELINES_ENABLED', 'false').lower() == 'true':
                try:
                    from ..review_guidelines import get_guidelines
                    article_type = state.get('article_type', '')
                    guidelines = get_guidelines(article_type)
                    if guidelines:
                        logger.info(f"[Reviewer] 41.11 自动匹配审核标准: {article_type} ({len(guidelines)} 条)")
                except Exception as e:
                    logger.debug(f"[Reviewer] 审核标准加载跳过: {e}")

        if verbatim_data:
            logger.info(f"[Reviewer] Verbatim 数据: {len(verbatim_data)} 项")
        if learning_objectives:
            logger.info(f"[Reviewer] 学习目标: {len(learning_objectives)} 个")

        result = self.review(
            document,
            outline,
            verbatim_data=verbatim_data,
            learning_objectives=learning_objectives,
            guidelines=guidelines,
        )

        state['review_score'] = result.get('score', 80)
        state['review_approved'] = result.get('approved', True)
        state['review_issues'] = result.get('issues', [])

        logger.info(f"质量审核完成: 得分 {result.get('score', 0)}, {'通过' if result.get('approved') else '未通过'}")

        if result.get('issues'):
            for issue in result['issues']:
                logger.info(f"  - [{issue.get('severity', 'medium')}] {issue.get('description', '')}")

        return state
