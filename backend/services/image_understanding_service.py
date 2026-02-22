"""
图片理解服务 — base64 图片编码 + vision 模型集成 + 图片分析

将图片读取、base64 编码、多模态分析封装为统一服务，
供博客生成管线中的任意 Agent 调用。
"""
import base64
import json
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

EXTENSION_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


@dataclass
class ViewedImage:
    """已查看的图片数据"""
    path: str
    base64: str
    mime_type: str


@dataclass
class ImageUnderstanding:
    """图片理解结果"""
    path: str
    description: str
    detected_text: Optional[str]
    image_type: str  # screenshot/diagram/chart/photo/code/other
    relevance_score: float  # 0-1


class ImageUnderstandingService:
    """
    图片理解服务

    职责：
    1. 读取图片并 base64 编码
    2. 调用多模态模型分析图片内容
    3. 管理已查看图片的状态
    """

    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self._viewed_images: Dict[str, ViewedImage] = {}

    def read_image(self, image_path: str) -> Optional[ViewedImage]:
        """读取图片并 base64 编码"""
        path = Path(image_path)

        if not path.is_absolute():
            logger.warning(f"路径必须为绝对路径: {image_path}")
            return None
        if not path.exists() or not path.is_file():
            logger.warning(f"图片文件不存在: {image_path}")
            return None
        if path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
            logger.warning(f"不支持的图片格式: {path.suffix}")
            return None

        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type is None:
            mime_type = EXTENSION_TO_MIME.get(path.suffix.lower(), "application/octet-stream")

        try:
            with open(path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"读取图片失败: {e}")
            return None

        viewed = ViewedImage(path=image_path, base64=img_base64, mime_type=mime_type)
        self._viewed_images[image_path] = viewed
        return viewed

    def analyze_image(
        self, image_path: str, context: str = ""
    ) -> Optional[ImageUnderstanding]:
        """读取并分析图片内容"""
        viewed = self._viewed_images.get(image_path) or self.read_image(image_path)
        if not viewed or not self.llm_service:
            return None

        prompt = self._build_analysis_prompt(context)
        response = self.llm_service.chat_with_image(
            prompt=prompt, image_base64=viewed.base64, mime_type=viewed.mime_type
        )
        if not response:
            return None

        return self._parse_response(image_path, response)

    def get_viewed_images(self) -> Dict[str, ViewedImage]:
        """获取所有已查看图片"""
        return dict(self._viewed_images)

    def clear_viewed_images(self):
        """清空已查看图片"""
        self._viewed_images.clear()

    def _build_analysis_prompt(self, context: str = "") -> str:
        """构建图片分析 Prompt"""
        prompt = (
            "请分析这张图片，返回 JSON：\n"
            '{"description": "图片内容描述(100-200字)", '
            '"detected_text": "图片中的文字(无则null)", '
            '"image_type": "screenshot|diagram|chart|photo|code|other", '
            '"relevance_score": 0.5}\n'
        )
        if context:
            prompt += f"\n上下文：{context[:500]}\n"
        return prompt

    def _parse_response(self, path: str, response: str) -> ImageUnderstanding:
        """解析模型响应"""
        try:
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
            data = json.loads(text)
            return ImageUnderstanding(
                path=path,
                description=data.get("description", ""),
                detected_text=data.get("detected_text"),
                image_type=data.get("image_type", "other"),
                relevance_score=float(data.get("relevance_score", 0.5)),
            )
        except (json.JSONDecodeError, ValueError):
            return ImageUnderstanding(
                path=path,
                description=response[:200],
                detected_text=None,
                image_type="other",
                relevance_score=0.5,
            )
