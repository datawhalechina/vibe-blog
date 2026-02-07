"""
Assembler Agent - 文档组装
"""

import logging
import re
from typing import Dict, Any, List

from ..prompts import get_prompt_manager
from ..utils.helpers import (
    replace_placeholders,
    estimate_reading_time
)

logger = logging.getLogger(__name__)


class AssemblerAgent:
    """
    文档组装师 - 负责最终文档组装
    """
    
    def __init__(self):
        """
        初始化 Assembler Agent
        """
        pass
    
    def extract_subheadings(self, content: str) -> List[str]:
        """
        从章节内容中提取二级标题（### 标题）
        
        Args:
            content: 章节内容
            
        Returns:
            二级标题列表
        """
        # 匹配 ### 开头的标题（不匹配 #### 及更多）
        pattern = r'^###\s+(.+?)$'
        matches = re.findall(pattern, content, re.MULTILINE)
        return matches[:3]  # 最多返回 3 个二级标题
    
    def assemble(
        self,
        outline: Dict[str, Any],
        sections: List[Dict[str, Any]],
        code_blocks: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        document_references: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        组装最终文档
        
        Args:
            outline: 大纲
            sections: 章节内容列表
            code_blocks: 代码块列表
            images: 图片资源列表
            document_references: 文档来源引用列表
            
        Returns:
            组装结果
        """
        pm = get_prompt_manager()
        
        # 1. 从章节内容中提取二级标题，构建目录数据
        toc_sections = []
        for section in sections:
            section_title = section.get('title', '')
            content = section.get('content', '')
            subheadings = self.extract_subheadings(content)
            toc_sections.append({
                'title': section_title,
                'subheadings': subheadings
            })
        
        # 2. 生成文章头部
        header = pm.render_assembler_header(
            title=outline.get('title', '技术博客'),
            subtitle=outline.get('subtitle', ''),
            reading_time=outline.get('reading_time', 30),
            core_value=outline.get('core_value', ''),
            table_of_contents=outline.get('table_of_contents', []),
            introduction=outline.get('introduction', ''),
            sections=toc_sections
        )
        
        # 3. 组装章节内容
        body_parts = []
        for section in sections:
            content = section.get('content', '')
            
            # 获取当前章节的 image_ids（由 artist agent 生成时记录）
            section_image_ids = section.get('image_ids', [])
            
            # 替换占位符，传入章节的 image_ids 用于精确匹配
            content = replace_placeholders(content, code_blocks, images, image_ids=section_image_ids)
            
            body_parts.append(content)
        
        body = '\n\n---\n\n'.join(body_parts)
        
        # 4. 生成文章尾部（支持分类展示参考来源）
        conclusion = outline.get('conclusion', {})
        footer = pm.render_assembler_footer(
            summary_points=conclusion.get('summary_points', []),
            next_steps=conclusion.get('next_steps', ''),
            reference_links=outline.get('reference_links', []),
            document_references=document_references or []
        )
        
        # 5. 组装完整文档
        full_document = header + body + footer
        
        # 6. 统计信息
        word_count = len(full_document)
        image_count = len(images)
        code_block_count = len(code_blocks)
        
        return {
            "markdown": full_document,
            "word_count": word_count,
            "image_count": image_count,
            "code_block_count": code_block_count
        }
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文档组装
        
        Args:
            state: 共享状态
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过文档组装: {state.get('error')}")
            state['final_markdown'] = ""
            return state
        
        outline = state.get('outline', {})
        sections = state.get('sections', [])
        if not outline or not sections:
            error_msg = "大纲或章节内容为空，无法进行文档组装"
            logger.error(error_msg)
            state['error'] = error_msg
            state['final_markdown'] = ""
            return state
        
        code_blocks = state.get('code_blocks', [])
        images = state.get('images', [])
        document_references = state.get('document_references', [])
        
        logger.info("开始组装文档")
        
        result = self.assemble(
            outline=outline,
            sections=sections,
            code_blocks=code_blocks,
            images=images,
            document_references=document_references
        )
        
        state['final_markdown'] = result.get('markdown', '')
        
        logger.info(f"文档组装完成: {result.get('word_count', 0)} 字, "
                   f"{result.get('image_count', 0)} 张图片, "
                   f"{result.get('code_block_count', 0)} 个代码块")
        
        return state
