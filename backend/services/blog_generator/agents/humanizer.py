"""
Humanizer Agent - 去除 AI 写作痕迹

在 Reviewer 之后、Assembler 之前，对每章内容进行 AI 味检测、评分和改写。
两步流程：先评分（轻量），评分低于阈值再改写（重量）。
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any

from ..prompts import get_prompt_manager

logger = logging.getLogger(__name__)


def _extract_source_placeholders(text: str) -> set:
    """提取文本中所有 {source_NNN} 占位符"""
    return set(re.findall(r'\{source_\d+\}', text))


def _extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON（处理 markdown 代码块、转义和截断问题）"""
    text = text.strip()
    if not text:
        raise ValueError("LLM 返回空内容，无法解析 JSON")
    # 提取 markdown 代码块中的 JSON
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
    # 如果提取后为空，尝试用正则找最外层 {...}
    if not text:
        raise ValueError("LLM 返回内容中未找到有效 JSON")

    # 多轮尝试解析
    for attempt_fn in [
        lambda t: json.loads(t),
        lambda t: json.loads(t, strict=False),
        lambda t: json.loads(re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', t), strict=False),
    ]:
        try:
            return attempt_fn(text)
        except json.JSONDecodeError:
            continue

    # 最后尝试：用正则提取最外层 {...} 块（应对 LLM 在 JSON 前后输出额外文本）
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group(), strict=False)
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("所有解析策略均失败", text, 0)


class HumanizerAgent:
    """
    去 AI 味 Agent — 检测并改写 AI 写作痕迹

    两步流程：先评分（轻量），评分低于阈值再改写。
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.skip_threshold = int(os.getenv('HUMANIZER_SKIP_THRESHOLD', '40'))
        self.max_retries = int(os.getenv('HUMANIZER_MAX_RETRIES', '1'))

        # 校验配置
        if not 0 <= self.skip_threshold <= 50:
            raise ValueError(
                f"HUMANIZER_SKIP_THRESHOLD 必须在 0-50 之间，当前值: {self.skip_threshold}"
            )

        logger.info(
            f"[Humanizer] 初始化完成 "
            f"(skip_threshold={self.skip_threshold}, max_retries={self.max_retries})"
        )

    def _score_section(self, content: str) -> Dict[str, Any]:
        """评分：检测 AI 写作痕迹（轻量调用）"""
        pm = get_prompt_manager()
        prompt = pm.render_humanizer_score(section_content=content)

        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        if not response:
            raise ValueError("LLM 评分返回空响应")
        return _extract_json(response)

    def _rewrite_section(self, content: str, audience_adaptation: str) -> Dict[str, Any]:
        """改写：去除 AI 写作痕迹（含重试）"""
        pm = get_prompt_manager()
        prompt = pm.render_humanizer(
            section_content=content,
            audience_adaptation=audience_adaptation,
        )

        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    caller="humanizer",
                )
                if not response or not response.strip():
                    raise ValueError("LLM 改写返回空响应")
                return _extract_json(response)
            except (json.JSONDecodeError, ValueError) as e:
                last_err = e
                # 记录 LLM 原始返回内容，方便排查
                resp_preview = repr(response[:200]) if response else "(None)"
                logger.warning(
                    f"[Humanizer] 改写解析失败 (attempt {attempt+1}/{self.max_retries+1}): {e} "
                    f"| response preview: {resp_preview}"
                )
                if attempt < self.max_retries:
                    time.sleep(2)
        # 所有重试失败，返回原文（用 humanized_content key 保持与 run() 一致）
        logger.warning(f"[Humanizer] 改写最终失败，保留原文: {last_err}")
        return {"humanized_content": content, "changes": [], "_fallback": True}

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行去 AI 味处理

        Args:
            state: 共享状态

        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"[Humanizer] 前置步骤失败，跳过: {state.get('error')}")
            return state

        sections = state.get('sections', [])
        if not sections:
            logger.warning("[Humanizer] 没有章节内容，跳过")
            return state

        audience = state.get('audience_adaptation', 'technical-beginner')

        total_sections = len(sections)
        skipped_count = 0
        rewritten_count = 0
        score_improvements = []
        start_time = time.time()

        for idx, section in enumerate(sections):
            title = section.get('title', f'章节{idx+1}')
            content = section.get('content', '')

            # 跳过空内容或仅标题的章节
            stripped = content.strip()
            if not stripped or stripped.startswith('#') and '\n' not in stripped:
                logger.info(f"[Humanizer] [{idx+1}/{total_sections}] {title} — 跳过（空内容）")
                skipped_count += 1
                continue

            section_start = time.time()
            original_placeholders = _extract_source_placeholders(content)

            # Step 1: 评分
            try:
                score_result = self._score_section(content)
            except Exception as e:
                logger.error(f"[Humanizer] [{idx+1}/{total_sections}] {title} — 评分异常: {e}，跳过")
                continue

            score = score_result.get('score', {})
            total_score = score.get('total', 0)
            elapsed = time.time() - section_start

            # 评分 >= 阈值，跳过改写
            if total_score >= self.skip_threshold:
                logger.info(
                    f"[Humanizer] [{idx+1}/{total_sections}] {title} — "
                    f"评分 {total_score}/50，跳过改写 ({elapsed:.1f}s)"
                )
                skipped_count += 1
                section['humanizer_score'] = total_score
                section['humanizer_skipped'] = True
                continue

            # Step 2: 改写
            try:
                rewrite_result = self._rewrite_section(content, audience)
            except Exception as e:
                logger.error(f"[Humanizer] [{idx+1}/{total_sections}] {title} — 改写异常: {e}，使用原始内容")
                section['humanizer_score'] = total_score
                section['humanizer_skipped'] = True
                skipped_count += 1
                continue

            humanized = rewrite_result.get('humanized_content')
            if not humanized or rewrite_result.get('_fallback'):
                logger.warning(f"[Humanizer] [{idx+1}/{total_sections}] {title} — 改写结果为空或回退，使用原始内容")
                section['humanizer_score'] = total_score
                section['humanizer_skipped'] = True
                skipped_count += 1
                continue

            # 验证占位符完整性
            new_placeholders = _extract_source_placeholders(humanized)
            if original_placeholders and not original_placeholders.issubset(new_placeholders):
                lost = original_placeholders - new_placeholders
                logger.error(
                    f"[Humanizer] [{idx+1}/{total_sections}] {title} — "
                    f"改写丢失占位符 {lost}，回退到原始内容"
                )
                section['humanizer_score'] = total_score
                section['humanizer_skipped'] = True
                section['humanizer_error'] = f"占位符丢失: {lost}"
                skipped_count += 1
                continue

            # 验证字数变化
            original_len = len(content)
            new_len = len(humanized)
            change_ratio = abs(new_len - original_len) / max(original_len, 1)
            if change_ratio > 0.1:
                logger.warning(
                    f"[Humanizer] [{idx+1}/{total_sections}] {title} — "
                    f"字数变化 {change_ratio:.0%} 超过 ±10% "
                    f"({original_len} → {new_len})"
                )

            # 重试逻辑：改写后重新评分，如果仍 < 35 则再改写一次
            retry_count = 0
            while retry_count < self.max_retries:
                try:
                    rescore = self._score_section(humanized)
                    new_score = rescore.get('score', {}).get('total', 0)
                    if new_score >= 35:
                        total_score = new_score
                        break
                    retry_count += 1
                    logger.info(
                        f"[Humanizer] [{idx+1}/{total_sections}] {title} — "
                        f"改写后评分 {new_score} < 35，重试 ({retry_count}/{self.max_retries})"
                    )
                    retry_result = self._rewrite_section(humanized, audience)
                    retry_humanized = retry_result.get('humanized_content')
                    if retry_humanized:
                        retry_placeholders = _extract_source_placeholders(retry_humanized)
                        if not original_placeholders or original_placeholders.issubset(retry_placeholders):
                            humanized = retry_humanized
                            total_score = new_score
                except Exception as e:
                    logger.error(f"[Humanizer] 重试失败: {e}")
                    break

            # 应用改写
            section['content'] = humanized
            section['humanizer_score_before'] = score.get('total', 0)
            section['humanizer_score_after'] = total_score
            section['humanizer_changes'] = rewrite_result.get('changes', [])
            section['humanizer_skipped'] = False
            rewritten_count += 1
            score_improvements.append(total_score - score.get('total', 0))
            elapsed = time.time() - section_start

            logger.info(
                f"[Humanizer] [{idx+1}/{total_sections}] {title} — "
                f"评分 {score.get('total', 0)} → {total_score}/50, "
                f"修改 {len(rewrite_result.get('changes', []))} 处 ({elapsed:.1f}s)"
            )

        total_elapsed = time.time() - start_time
        avg_improvement = sum(score_improvements) / len(score_improvements) if score_improvements else 0

        logger.info(
            f"[Humanizer] 完成: {total_sections} 章, "
            f"跳过 {skipped_count}, 改写 {rewritten_count}, "
            f"平均提升 {avg_improvement:+.1f} 分, "
            f"耗时 {total_elapsed:.1f}s"
        )

        return state
