"""
41.05 图片预规划 — 全局图片计划 + 预生成

在 Planner 完成大纲后、Writer 开始前：
1. 分析大纲 + 研究素材，生成全局图片计划
2. 标记哪些图片可以预生成（不依赖写作内容）
3. 预生成的图片在 ArtistAgent 阶段直接复用，跳过重复生成

环境变量：
- IMAGE_PREPLAN_ENABLED: 是否启用（默认 false）
- IMAGE_PREPLAN_MAX_IMAGES: 预规划最大图片数（默认 8）
"""
import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        text = text[start:end].strip() if end != -1 else text[start:].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        text = text[start:end].strip() if end != -1 else text[start:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


class ImagePreplanner:
    """全局图片预规划器"""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.max_images = int(os.environ.get('IMAGE_PREPLAN_MAX_IMAGES', '8'))

    def plan(self, outline: Dict[str, Any],
             background_knowledge: str = "",
             article_type: str = "tutorial") -> List[Dict]:
        """
        基于大纲生成全局图片计划。

        Returns:
            图片计划列表: [{'section_id': str, 'image_type': str,
                           'description': str, 'can_pregenerate': bool,
                           'priority': int}]
        """
        sections = outline.get('sections', [])
        if not sections:
            return []

        sections_text = "\n".join(
            f"- [{s.get('id', i)}] {s.get('title', '')}: {s.get('description', '')}"
            for i, s in enumerate(sections)
        )

        prompt = f"""你是一位技术文章配图规划师。根据以下文章大纲，规划全局配图方案。

文章类型: {article_type}
背景知识摘要: {background_knowledge[:500] if background_knowledge else '无'}

大纲章节:
{sections_text}

请为每个需要配图的章节规划图片，输出 JSON 数组。每个元素包含:
- section_id: 章节 ID
- image_type: 图片类型（flowchart/infographic/comparison/timeline/scene/framework）
- description: 图片描述（50-100字，具体到内容）
- can_pregenerate: 是否可以预生成（true=不依赖写作内容，false=需要写作内容后才能生成）
- priority: 优先级（1=最高，3=最低）

规则:
1. 不是每个章节都需要配图，只为内容复杂或需要可视化的章节规划
2. 总图片数不超过 {self.max_images} 张
3. 概念性/架构性图片通常可以预生成
4. 代码示例相关的图片不能预生成

输出纯 JSON 数组，不要其他内容。"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result = _extract_json(response)

            # 兼容 LLM 返回 {images: [...]} 或直接 [...]
            if isinstance(result, dict):
                plan = result.get('images', result.get('plan', []))
            elif isinstance(result, list):
                plan = result
            else:
                plan = []

            # 截断到 max_images
            plan = plan[:self.max_images]

            pregenerable = sum(1 for p in plan if p.get('can_pregenerate'))
            logger.info(
                f"[ImagePreplan] 规划完成: {len(plan)} 张图片, "
                f"{pregenerable} 张可预生成"
            )
            return plan

        except Exception as e:
            logger.warning(f"[ImagePreplan] 规划失败: {e}")
            return []
