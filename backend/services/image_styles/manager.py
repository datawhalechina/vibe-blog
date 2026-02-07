"""
图片风格管理器 - 基于 Jinja2 模板的分离式管理
"""
import logging
from typing import Dict, List, Optional
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# 模板和配置目录指向 infrastructure/prompts/image_styles/
INFRA_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "prompts" / "image_styles"
TEMPLATES_DIR = INFRA_DIR
STYLES_CONFIG = INFRA_DIR / "styles.yaml"


class ImageStyleManager:
    """图片风格管理器"""
    
    _instance = None
    _styles: Dict = {}
    _env: Environment = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载风格配置和模板"""
        try:
            # 加载 styles.yaml
            with open(STYLES_CONFIG, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self._styles = config.get('styles', {})
            
            # 初始化 Jinja2 环境
            self._env = Environment(
                loader=FileSystemLoader(TEMPLATES_DIR),
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            logger.info(f"已加载 {len(self._styles)} 个图片风格")
        except Exception as e:
            logger.error(f"加载风格配置失败: {e}")
            self._styles = {}
    
    def reload(self):
        """热重载配置和模板"""
        self._load_config()
        logger.info("图片风格配置已重新加载")
    
    def get_style(self, style_id: str) -> Optional[Dict]:
        """获取指定风格配置"""
        style = self._styles.get(style_id)
        if style:
            return {"id": style_id, **style}
        return None
    
    def get_default_style_id(self) -> str:
        """获取默认风格 ID"""
        for style_id, style in self._styles.items():
            if style.get('default'):
                return style_id
        return list(self._styles.keys())[0] if self._styles else "cartoon"
    
    def get_all_styles(self) -> List[Dict]:
        """获取所有可用风格（用于前端下拉框）"""
        return [
            {
                "id": style_id,
                "name": style.get("name", style_id),
                "name_en": style.get("name_en", ""),
                "description": style.get("description", ""),
                "icon": style.get("icon", "🎨"),
                "default": style.get("default", False)
            }
            for style_id, style in self._styles.items()
        ]
    
    def render_prompt(self, style_id: str, content: str) -> str:
        """
        渲染指定风格的 Prompt
        
        Args:
            style_id: 风格 ID
            content: 要填充的内容
            
        Returns:
            渲染后的完整 Prompt
        """
        style = self._styles.get(style_id)
        if not style:
            logger.warning(f"未找到风格 {style_id}，使用默认风格")
            style_id = self.get_default_style_id()
            style = self._styles.get(style_id)
        
        if not style:
            logger.error("无法获取任何风格配置")
            return content
        
        template_file = style.get("template", f"{style_id}.j2")
        
        try:
            template = self._env.get_template(template_file)
            return template.render(content=content)
        except Exception as e:
            logger.error(f"渲染模板 {template_file} 失败: {e}")
            return content
    
    def is_valid_style(self, style_id: str) -> bool:
        """检查风格 ID 是否有效"""
        return style_id in self._styles


# 全局单例
_manager: Optional[ImageStyleManager] = None


def get_style_manager() -> ImageStyleManager:
    """获取风格管理器单例"""
    global _manager
    if _manager is None:
        _manager = ImageStyleManager()
    return _manager
