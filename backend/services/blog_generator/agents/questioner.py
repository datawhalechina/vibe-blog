"""
Questioner Agent - 追问深化
"""

import json
import logging
from typing import Dict, Any, List

from ..prompts import get_prompt_manager

logger = logging.getLogger(__name__)


class QuestionerAgent:
    """
    追问师 - 负责发现内容模糊点并提出深化问题
    """
    
    def __init__(self, llm_client):
        """
        初始化 Questioner Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    def check_depth(
        self,
        section_content: str,
        section_outline: Dict[str, Any],
        depth_requirement: str = "medium"
    ) -> Dict[str, Any]:
        """
        检查章节内容深度
        
        Args:
            section_content: 章节内容
            section_outline: 章节大纲
            depth_requirement: 深度要求
            
        Returns:
            检查结果
        """
        pm = get_prompt_manager()
        prompt = pm.render_questioner(
            section_content=section_content,
            section_outline=section_outline,
            depth_requirement=depth_requirement
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return {
                "is_detailed_enough": result.get("is_detailed_enough", True),
                "depth_score": result.get("depth_score", 80),
                "vague_points": result.get("vague_points", [])
            }
            
        except Exception as e:
            logger.error(f"深度检查失败: {e}")
            # 默认通过
            return {
                "is_detailed_enough": True,
                "depth_score": 80,
                "vague_points": []
            }
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行追问检查
        
        Args:
            state: 共享状态
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过追问检查: {state.get('error')}")
            return state
        
        sections = state.get('sections', [])
        if not sections:
            logger.warning("没有章节内容，跳过追问检查")
            state['question_results'] = []
            state['all_sections_detailed'] = True
            return state
        
        outline = state.get('outline', {})
        sections_outline = outline.get('sections', [])
        
        # 根据目标长度确定深度要求
        target_length = state.get('target_length', 'medium')
        depth_map = {
            'mini': 'minimal',    # mini 模式使用最低深度要求
            'short': 'shallow',
            'medium': 'medium',
            'long': 'deep',
            'custom': 'medium'    # 自定义模式使用中等深度
        }
        depth_requirement = depth_map.get(target_length, 'medium')
        
        logger.info(f"开始追问检查 (深度要求: {depth_requirement})")
        
        question_results = []
        all_detailed = True
        
        for i, section in enumerate(sections):
            section_outline = sections_outline[i] if i < len(sections_outline) else {}
            
            result = self.check_depth(
                section_content=section.get('content', ''),
                section_outline=section_outline,
                depth_requirement=depth_requirement
            )
            
            question_result = {
                "section_id": section.get('id', f'section_{i+1}'),
                "is_detailed_enough": result.get('is_detailed_enough', True),
                "depth_score": result.get('depth_score', 80),
                "vague_points": result.get('vague_points', [])
            }
            question_results.append(question_result)
            
            if not result.get('is_detailed_enough', True):
                all_detailed = False
                logger.info(f"章节需要深化: {section.get('title', '')} (得分: {result.get('depth_score', 0)})")
        
        state['question_results'] = question_results
        state['all_sections_detailed'] = all_detailed
        
        logger.info(f"追问检查完成: {'全部通过' if all_detailed else '需要深化'}")
        
        return state
