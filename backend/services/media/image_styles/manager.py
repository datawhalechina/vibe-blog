"""
图片风格管理器 - 基于 Jinja2 模板的分离式管理

支持 Type × Style 二维渲染：
- Type（插图类型）：定义信息骨架（infographic/scene/flowchart/comparison/framework/timeline）
- Style（视觉风格）：定义视觉皮肤（cartoon/academic/ink_wash/...）
- 兼容性矩阵：确保 Type 和 Style 的组合合理
"""
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# 模板和配置目录指向 infrastructure/prompts/image_styles/
INFRA_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "infrastructure"
    / "prompts"
    / "image_styles"
)
TEMPLATES_DIR = INFRA_DIR
STYLES_CONFIG = INFRA_DIR / "styles.yaml"


class ImageStyleManager:
    """图片风格管理器（Type × Style 二维系统）"""

    _instance = None
    _styles: Dict = {}
    _types: Dict = {}
    _compatibility: Dict = {}
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
                self._types = config.get('types', {})
                self._compatibility = config.get('compatibility', {})

            # 初始化 Jinja2 环境
            self._env = Environment(
                loader=FileSystemLoader(TEMPLATES_DIR),
                trim_blocks=True,
                lstrip_blocks=True
            )

            logger.info(f"已加载 {len(self._styles)} 个图片风格, {len(self._types)} 个插图类型")
        except Exception as e:
            logger.error(f"加载风格配置失败: {e}")
            self._styles = {}
            self._types = {}
            self._compatibility = {}

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

    def render_prompt(self, style_id: str, content: str, illustration_type: str = "") -> str:
        """
        渲染指定风格的 Prompt（支持 Type × Style 二维渲染）

        渲染顺序：先 Type（结构骨架） → 再 Style（视觉皮肤）

        Args:
            style_id: 风格 ID
            content: 要填充的内容
            illustration_type: 插图类型 ID（可选，为空则跳过 Type 渲染）

        Returns:
            渲染后的完整 Prompt
        """
        # Step 1: 兼容性检查与降级
        if illustration_type:
            style_id, illustration_type = self.resolve_compatibility(
                style_id, illustration_type
            )

        # Step 2: Type 渲染（结构骨架）
        type_content = content
        if illustration_type and illustration_type in self._types:
            type_config = self._types[illustration_type]
            type_template_file = type_config.get("template", f"types/{illustration_type}.j2")
            try:
                type_template = self._env.get_template(type_template_file)
                type_content = type_template.render(content=content)
                logger.debug(f"Type 模板渲染完成: {illustration_type}")
            except Exception as e:
                logger.warning(f"Type 模板 {type_template_file} 渲染失败: {e}，使用原始内容")

        # Step 3: Style 渲染（视觉皮肤）
        style = self._styles.get(style_id)
        if not style:
            logger.warning(f"未找到风格 {style_id}，使用默认风格")
            style_id = self.get_default_style_id()
            style = self._styles.get(style_id)

        if not style:
            logger.error("无法获取任何风格配置")
            return type_content

        template_file = style.get("template", f"{style_id}.j2")

        try:
            template = self._env.get_template(template_file)
            return template.render(content=type_content)
        except Exception as e:
            logger.error(f"Style 模板 {template_file} 渲染失败: {e}")
            return type_content

    def is_valid_style(self, style_id: str) -> bool:
        """检查风格 ID 是否有效"""
        return style_id in self._styles

    def is_valid_type(self, type_id: str) -> bool:
        """检查插图类型 ID 是否有效"""
        return type_id in self._types

    def get_all_types(self) -> List[Dict]:
        """获取所有可用插图类型"""
        return [
            {
                "id": type_id,
                "name": t.get("name", type_id),
                "name_en": t.get("name_en", ""),
                "description": t.get("description", ""),
            }
            for type_id, t in self._types.items()
        ]

    def get_compatibility(self, type_id: str, style_id: str) -> str:
        """
        查询 Type × Style 兼容性

        Returns:
            "recommended" / "acceptable" / "incompatible" / "unknown"
        """
        type_compat = self._compatibility.get(type_id, {})
        return type_compat.get(style_id, "unknown")

    def resolve_compatibility(
        self, style_id: str, illustration_type: str
    ) -> Tuple[str, str]:
        """
        兼容性检查与降级策略

        如果 Type × Style 不兼容，尝试：
        1. 保留 Style，从该 Style 的 best_types 中选一个最接近的 Type
        2. 如果无法降级，清除 illustration_type（退回纯 Style 模式）

        Args:
            style_id: 风格 ID
            illustration_type: 插图类型 ID

        Returns:
            (resolved_style_id, resolved_illustration_type)
        """
        compat = self.get_compatibility(illustration_type, style_id)

        if compat in ("recommended", "acceptable", "unknown"):
            return style_id, illustration_type

        # incompatible: 尝试降级
        logger.warning(
            f"Type×Style 不兼容: {illustration_type} × {style_id} → 尝试降级"
        )

        # 策略：保留 Style，从 best_types 中选一个替代 Type
        style = self._styles.get(style_id, {})
        best_types = style.get("best_types", [])
        if best_types:
            fallback_type = best_types[0]
            logger.info(
                f"降级 Type: {illustration_type} → {fallback_type} (Style={style_id})"
            )
            return style_id, fallback_type

        # 无法降级，清除 Type
        logger.info(
            f"无法降级，清除 Type: {illustration_type} (Style={style_id})"
        )
        return style_id, ""

    def auto_recommend_type(self, content: str) -> str:
        """
        根据内容自动推荐插图类型

        Args:
            content: 章节内容文本

        Returns:
            推荐的 illustration_type ID
        """
        from .type_signals import auto_recommend_type
        return auto_recommend_type(content)


# 全局单例
_manager: Optional[ImageStyleManager] = None


def get_style_manager() -> ImageStyleManager:
    """获取风格管理器单例"""
    global _manager
    if _manager is None:
        _manager = ImageStyleManager()
    return _manager
