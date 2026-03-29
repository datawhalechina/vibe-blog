"""
图片提取器 - 从 Markdown 中提取图片引用

功能:
- 扫描 Markdown 中的图片引用
- 解析图片路径 (本地/外链)
- 验证图片是否存在
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """图片信息"""
    alt_text: str           # alt 文本
    src: str                # 原始路径
    is_external: bool       # 是否外链
    local_path: Optional[str]  # 本地绝对路径
    exists: bool            # 文件是否存在
    position: int           # 在文档中的位置 (行号)


class ImageExtractor:
    """图片提取器"""
    
    # 支持的图片格式
    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
    
    def extract_images(self, content: str, base_path: str = None) -> List[ImageInfo]:
        """
        从 Markdown 内容中提取图片
        
        Args:
            content: Markdown 内容
            base_path: 文件所在目录 (用于解析相对路径)
            
        Returns:
            图片信息列表
        """
        images = []
        
        # 匹配 Markdown 图片语法: ![alt](src)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(pattern, line):
                alt_text = match.group(1)
                src = match.group(2).strip()
                
                # 移除可能的标题部分 ![alt](src "title")
                if ' ' in src:
                    src = src.split(' ')[0]
                if '"' in src:
                    src = src.split('"')[0].strip()
                
                image_info = self._parse_image(alt_text, src, base_path, line_num)
                if image_info:
                    images.append(image_info)
        
        # 匹配 HTML img 标签
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>'
        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(html_pattern, line, re.IGNORECASE):
                src = match.group(1)
                alt_text = match.group(2) or ''
                
                image_info = self._parse_image(alt_text, src, base_path, line_num)
                if image_info:
                    images.append(image_info)
        
        logger.debug(f"提取到 {len(images)} 张图片")
        return images
    
    def _parse_image(self, alt_text: str, src: str, base_path: str, position: int) -> Optional[ImageInfo]:
        """解析单个图片"""
        # 检查是否为外链
        is_external = self._is_external_url(src)
        
        local_path = None
        exists = False
        
        if not is_external and base_path:
            # 解析本地路径
            if src.startswith('/'):
                # 绝对路径 (相对于仓库根目录)
                # 需要找到仓库根目录
                local_path = src
            else:
                # 相对路径
                local_path = os.path.normpath(os.path.join(base_path, src))
            
            exists = os.path.isfile(local_path)
        elif is_external:
            exists = True  # 假设外链存在
        
        # 检查扩展名
        ext = os.path.splitext(src)[1].lower()
        if ext and ext not in self.SUPPORTED_EXTENSIONS:
            return None
        
        return ImageInfo(
            alt_text=alt_text,
            src=src,
            is_external=is_external,
            local_path=local_path,
            exists=exists,
            position=position,
        )
    
    def _is_external_url(self, src: str) -> bool:
        """检查是否为外部 URL"""
        if src.startswith(('http://', 'https://', '//')):
            return True
        
        parsed = urlparse(src)
        return bool(parsed.scheme and parsed.netloc)
    
    def get_local_images(self, images: List[ImageInfo]) -> List[ImageInfo]:
        """获取本地存在的图片"""
        return [img for img in images if not img.is_external and img.exists]
    
    def get_missing_images(self, images: List[ImageInfo]) -> List[ImageInfo]:
        """获取缺失的图片"""
        return [img for img in images if not img.is_external and not img.exists]
