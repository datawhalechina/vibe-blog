"""
Writer Agent - 内容撰写
"""

import json
import logging
from typing import Dict, Any, List

from ..prompts.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)


class WriterAgent:
    """
    内容撰写师 - 负责章节正文撰写
    """
    
    def __init__(self, llm_client):
        """
        初始化 Writer Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    def write_section(
        self,
        section_outline: Dict[str, Any],
        previous_section_summary: str = "",
        next_section_preview: str = "",
        background_knowledge: str = ""
    ) -> Dict[str, Any]:
        """
        撰写单个章节
        
        Args:
            section_outline: 章节大纲
            previous_section_summary: 前一章节摘要
            next_section_preview: 后续章节预告
            background_knowledge: 背景知识
            
        Returns:
            章节内容
        """
        pm = get_prompt_manager()
        prompt = pm.render_writer(
            section_outline=section_outline,
            previous_section_summary=previous_section_summary,
            next_section_preview=next_section_preview,
            background_knowledge=background_knowledge
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "id": section_outline.get('id', ''),
                "title": section_outline.get('title', ''),
                "content": response,
                "image_ids": [],
                "code_ids": []
            }
            
        except Exception as e:
            logger.error(f"章节撰写失败 [{section_outline.get('title', '')}]: {e}")
            raise
    
    def enhance_section(
        self,
        original_content: str,
        vague_points: List[Dict[str, Any]],
        section_title: str = "",
        progress_info: str = ""
    ) -> str:
        """
        根据追问深化章节内容
        
        Args:
            original_content: 原始内容
            vague_points: 模糊点列表
            section_title: 章节标题
            progress_info: 进度信息 (如 "[1/3]")
            
        Returns:
            增强后的内容
        """
        if not vague_points:
            return original_content
        
        display_title = section_title if section_title else "(未知章节)"
        display_progress = progress_info if progress_info else ""
        logger.info(f"正在深化章节 {display_progress} {display_title}")
        
        pm = get_prompt_manager()
        prompt = pm.render_writer_enhance(
            original_content=original_content,
            vague_points=vague_points
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            return response
            
        except Exception as e:
            logger.error(f"章节深化失败: {e}")
            return original_content
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行内容撰写
        
        Args:
            state: 共享状态
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过内容撰写: {state.get('error')}")
            return state
        
        outline = state.get('outline')
        if outline is None:
            error_msg = "大纲为空，无法进行内容撰写"
            logger.error(error_msg)
            state['error'] = error_msg
            return state
        
        sections_outline = outline.get('sections', [])
        background_knowledge = state.get('background_knowledge', '')
        
        logger.info(f"开始撰写内容: {len(sections_outline)} 个章节")
        
        sections = []
        for i, section_outline in enumerate(sections_outline):
            # 获取上下文
            prev_summary = ""
            next_preview = ""
            
            if i > 0:
                prev_section = sections_outline[i - 1]
                prev_summary = f"上一章节《{prev_section.get('title', '')}》讨论了 {prev_section.get('key_concept', '')}"
            
            if i < len(sections_outline) - 1:
                next_section = sections_outline[i + 1]
                next_preview = f"下一章节《{next_section.get('title', '')}》将介绍 {next_section.get('key_concept', '')}"
            
            try:
                section = self.write_section(
                    section_outline=section_outline,
                    previous_section_summary=prev_summary,
                    next_section_preview=next_preview,
                    background_knowledge=background_knowledge
                )
                sections.append(section)
                logger.info(f"章节撰写完成: {section.get('title', '')}")
                
            except Exception as e:
                logger.error(f"章节撰写失败: {e}")
                state['error'] = f"章节撰写失败: {str(e)}"
                break
        
        state['sections'] = sections
        logger.info(f"内容撰写完成: {len(sections)} 个章节")
        
        return state
