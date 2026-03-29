"""
SummaryGenerator Agent - 博客导读 + SEO 关键词生成

在 Assembler 之后运行，用 1 次 LLM 调用生成：
  - TL;DR 导读（2-3 句）
  - SEO 关键词（10-15 个）
  - 社交媒体摘要（50-100 字）
  - Meta Description（150 字以内）
"""

import json
import logging
from typing import Dict, Any

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

class SummaryGeneratorAgent:
    """博客导读 + SEO 关键词生成 Agent"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def generate(self, title: str, full_article: str,
                 learning_objectives: list = None) -> Dict[str, Any]:
        """生成摘要"""
        pm = get_prompt_manager()
        prompt = pm.render_summary_generator(
            title=title,
            full_article=full_article,
            learning_objectives=learning_objectives or [],
        )
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        if not response or not response.strip():
            raise ValueError("LLM 摘要生成返回空响应")
        return _extract_json(response)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行摘要生成并写入 state"""
        if state.get('error'):
            return state

        full_article = state.get('final_markdown', '')
        if not full_article:
            logger.info("[SummaryGenerator] 无文章内容，跳过")
            return state

        title = (state.get('outline') or {}).get('title', '')
        learning_objectives = (state.get('outline') or {}).get(
            'learning_objectives', []
        )

        try:
            result = self.generate(title, full_article, learning_objectives)
        except Exception as e:
            logger.error(f"[SummaryGenerator] 生成异常: {e}")
            return state

        # 将 TL;DR 插入文章开头
        tldr = result.get('tldr', '')
        if tldr:
            tldr_block = f"> **TL;DR** {tldr}\n\n---\n\n"
            state['final_markdown'] = tldr_block + full_article

        # 保存到 state
        state['seo_keywords'] = result.get('seo_keywords', [])
        state['social_summary'] = result.get('social_summary', '')
        state['meta_description'] = result.get('meta_description', '')

        logger.info(
            f"[SummaryGenerator] 完成: "
            f"TL;DR={len(tldr)}字, "
            f"SEO={len(result.get('seo_keywords', []))}个, "
            f"社交摘要={len(result.get('social_summary', ''))}字"
        )
        return state
