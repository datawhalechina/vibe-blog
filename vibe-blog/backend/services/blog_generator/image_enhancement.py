"""
ImageEnhancementPipeline — code2prompt 图片增强管线

将 Mermaid/SVG 代码骨架图通过两步转换变为精美信息图：
  Step 1: code2prompt — LLM 将代码结构翻译为详细的图片描述
  Step 2: prompt2image — AI 图片生成 API 根据描述生成精美图片

核心原则：增强是可选的锦上添花，失败不影响正常流程。
"""

import logging
import os
from typing import Optional

from ..image_service import get_image_service, AspectRatio, ImageSize

logger = logging.getLogger(__name__)

# 增强超时（秒）
ENHANCEMENT_TIMEOUT = int(os.getenv("IMAGE_ENHANCEMENT_TIMEOUT", "60"))

# 适合增强的 Mermaid 图表类型（时序图等 Mermaid 渲染已足够好）
ENHANCEABLE_TYPES = {"flowchart", "graph", "classDiagram", "stateDiagram", "erDiagram", "mindmap"}


def _get_mermaid_type(code: str) -> str:
    """从 Mermaid 代码提取图表类型关键字"""
    first_line = code.strip().split("\n")[0].strip() if code.strip() else ""
    for t in ENHANCEABLE_TYPES:
        if first_line.lower().startswith(t.lower()):
            return t
    return ""


class ImageEnhancementPipeline:
    """图片增强管线 — 将代码骨架图转为精美信息图"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def enhance(
        self,
        code: str,
        render_method: str,
        caption: str,
        style: str = "扁平化信息图",
        image_style: str = "",
    ) -> Optional[str]:
        """
        增强配图质量。

        Args:
            code: Mermaid/SVG 代码
            render_method: "mermaid" | "svg"
            caption: 图片说明
            style: 目标视觉风格描述
            image_style: 图片风格 ID（传给 style_manager）

        Returns:
            增强后的图片路径/URL，失败返回 None（回退到原始渲染）
        """
        # 仅对适合增强的图表类型执行
        if render_method == "mermaid":
            mermaid_type = _get_mermaid_type(code)
            if not mermaid_type:
                logger.debug("code2prompt: 图表类型不在增强范围内，跳过")
                return None

        # Step 1: code → detailed prompt
        image_prompt = self._code_to_prompt(code, render_method, caption, style)
        if not image_prompt:
            return None

        # Step 2: prompt → image
        return self._generate_enhanced_image(image_prompt, style, image_style)

    # ------------------------------------------------------------------
    # Step 1: code2prompt
    # ------------------------------------------------------------------

    def _code_to_prompt(
        self,
        code: str,
        render_method: str,
        caption: str,
        style: str,
    ) -> Optional[str]:
        """将 Mermaid/SVG 代码翻译为详细的图片生成 prompt"""
        from .prompts import get_prompt_manager

        pm = get_prompt_manager()
        prompt = pm.render_code2prompt(
            code=code,
            render_method=render_method,
            caption=caption,
            style=style,
        )

        try:
            response = self.llm.chat(messages=[{"role": "user", "content": prompt}])
            result = response.strip()
            if len(result) < 50:
                logger.warning("code2prompt: LLM 返回内容过短，跳过增强")
                return None
            logger.info(f"code2prompt: 翻译完成 ({len(result)} 字符)")
            return result
        except Exception as e:
            logger.error(f"code2prompt: LLM 调用失败: {e}")
            return None

    # ------------------------------------------------------------------
    # Step 2: prompt2image
    # ------------------------------------------------------------------

    def _generate_enhanced_image(
        self,
        image_prompt: str,
        style: str,
        image_style: str = "",
    ) -> Optional[str]:
        """用详细 prompt 生成精美信息图"""
        image_service = get_image_service()
        if not image_service or not image_service.is_available():
            logger.warning("code2prompt: 图片生成服务不可用，跳过增强")
            return None

        try:
            # 如果有风格 ID，走 style_manager 渲染
            if image_style:
                from services.image_styles import get_style_manager
                full_prompt = get_style_manager().render_prompt(
                    image_style, image_prompt, illustration_type="infographic"
                )
            else:
                full_prompt = (
                    f"请根据以下详细描述生成一张精美的信息图。\n\n"
                    f"风格要求：{style}\n"
                    f"构图：横版 16:9\n"
                    f"要求：所有中文文字必须清晰可读，布局整洁专业\n\n"
                    f"详细描述：\n{image_prompt}"
                )

            result = image_service.generate(
                prompt=full_prompt,
                aspect_ratio=AspectRatio.LANDSCAPE_16_9,
                image_size=ImageSize.SIZE_2K,
                max_wait_time=ENHANCEMENT_TIMEOUT,
            )

            if result and (result.oss_url or result.local_path):
                final_path = result.oss_url or result.local_path
                logger.info(f"code2prompt: 增强图片生成成功: {final_path}")
                return final_path

            logger.warning("code2prompt: 图片生成返回空结果")
            return None

        except Exception as e:
            logger.error(f"code2prompt: 增强图片生成失败: {e}")
            return None
