"""
Prompt 管理器

加载和渲染 vibe_reviewer 的 Prompt 模板
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# 模板目录
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Jinja2 环境
_jinja_env: Optional[Environment] = None


def get_jinja_env() -> Environment:
    """获取 Jinja2 环境"""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


class PromptManager:
    """Prompt 管理器"""
    
    def __init__(self):
        self.env = get_jinja_env()
    
    def render(self, template_name: str, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            template_name: 模板名称 (不含 .j2 后缀)
            **kwargs: 模板变量
            
        Returns:
            渲染后的 Prompt
        """
        template = self.env.get_template(f"{template_name}.j2")
        return template.render(**kwargs)
    
    def render_analyze(self, content: str) -> str:
        """渲染内容分析 Prompt"""
        return self.render("analyze", content=content)
    
    def render_depth_check(self, content: str, references: list = None) -> str:
        """渲染深度检查 Prompt"""
        return self.render("depth_check", content=content, references=references or [])
    
    def render_quality_review(self, content: str, references: list = None) -> str:
        """渲染质量审核 Prompt"""
        return self.render("quality_review", content=content, references=references or [])
    
    def render_readability_check(self, content: str, metrics: Dict = None) -> str:
        """渲染可读性检测 Prompt"""
        return self.render("readability_check", content=content, metrics=metrics or {})
    
    def render_improvement(
        self, 
        content: str, 
        depth_result: Dict, 
        quality_result: Dict, 
        readability_result: Dict
    ) -> str:
        """渲染改进建议 Prompt"""
        return self.render(
            "improvement",
            content=content,
            depth_result=depth_result,
            quality_result=quality_result,
            readability_result=readability_result,
        )


# 全局实例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取 Prompt 管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
