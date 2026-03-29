"""
多模态处理模块

复用 vibe-blog 的多模态接入方式:
- IMAGE_CAPTION_MODEL=qwen3-vl-plus-2025-12-19
- llm_service.chat_with_image()
"""

from .image_analyzer import ImageAnalyzer

__all__ = [
    'ImageAnalyzer',
]
