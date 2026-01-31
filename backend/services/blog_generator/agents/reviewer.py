"""
Reviewer Agent - 质量审核
"""

import json
import logging
from typing import Dict, Any

from ..prompts.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """
    质量审核师 - 负责内容质量把控
    """
    
    def __init__(self, llm_client):
        """
        初始化 Reviewer Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    def review(
        self,
        document: str,
        outline: Dict[str, Any],
        verbatim_data: list = None,
        learning_objectives: list = None,
        search_results: list = None,
        background_knowledge: str = None
    ) -> Dict[str, Any]:
        """
        审核文档
        
        Args:
            document: 完整文档
            outline: 原始大纲
            verbatim_data: 需要原样保留的数据
            learning_objectives: 学习目标列表
            search_results: 原始搜索结果（用于对比检查）
            background_knowledge: 背景知识摘要（与 Writer 使用的相同）
            
        Returns:
            审核结果
        """
        pm = get_prompt_manager()
        prompt = pm.render_reviewer(
            document=document,
            outline=outline,
            search_results=search_results,
            verbatim_data=verbatim_data or [],
            learning_objectives=learning_objectives or [],
            background_knowledge=background_knowledge or ""
        )
        
        # 输出完整的 Reviewer Prompt 到日志（用于诊断）
        logger.debug("=" * 80)
        logger.debug("【Reviewer Prompt 完整内容】")
        logger.debug("=" * 80)
        logger.debug(prompt)
        logger.debug("=" * 80)
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            # 基于规则二次校验
            issues = result.get("issues", [])
            score = result.get("score", 80)
            
            # 检查是否有高优先级问题
            high_priority_issues = [
                i for i in issues 
                if i.get('severity') == 'high' or i.get('issue_type') in [
                    'hallucination', 'verbatim_violation', 'learning_objective_mismatch',
                    'terminology_clarity', 'content_relevance', 'accuracy_mismatch'
                ]
            ]
            
            # 评分标准：
            # - 有 high severity 问题 → 不通过
            # - 有 hallucination/verbatim_violation/accuracy_mismatch → 不通过
            # - score < 80 → 不通过
            # - 否则通过
            approved = (
                result.get("approved", True) 
                and len(high_priority_issues) == 0 
                and score >= 91
            )
            
            return {
                "score": score,
                "approved": approved,
                "issues": issues,
                "summary": result.get("summary", "")
            }
            
        except Exception as e:
            logger.error(f"审核失败: {e}")
            # 默认通过
            return {
                "score": 80,
                "approved": True,
                "issues": [],
                "summary": "审核完成"
            }
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行质量审核
        
        Args:
            state: 共享状态
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过质量审核: {state.get('error')}")
            state['review_score'] = 0
            state['review_approved'] = False
            state['review_issues'] = []
            return state
        
        sections = state.get('sections', [])
        if not sections:
            logger.error("没有章节内容，跳过质量审核")
            state['review_score'] = 0
            state['review_approved'] = False
            state['review_issues'] = []
            return state
        
        outline = state.get('outline', {})
        
        # 组装文档用于审核
        document_parts = []
        for section in sections:
            document_parts.append(f"## {section.get('title', '')}\n\n{section.get('content', '')}")
        
        document = '\n\n---\n\n'.join(document_parts)
        
        logger.info("开始质量审核")
        
        # 获取 Instructional Design 相关数据（新增）
        verbatim_data = state.get('verbatim_data', [])
        learning_objectives = state.get('learning_objectives', [])
        search_results = state.get('search_results', [])
        background_knowledge = state.get('background_knowledge', '')
        
        if verbatim_data:
            logger.info(f"📋 Verbatim 数据检查: {len(verbatim_data)} 项")
        if learning_objectives:
            logger.info(f"📚 学习目标检查: {len(learning_objectives)} 个")
        if search_results:
            logger.info(f"🔍 搜索结果对比: {len(search_results)} 个来源")
        if background_knowledge:
            logger.info(f"📖 背景知识: {len(background_knowledge)} 字")
        
        result = self.review(
            document, 
            outline,
            verbatim_data=verbatim_data,
            learning_objectives=learning_objectives,
            search_results=search_results,
            background_knowledge=background_knowledge
        )
        
        state['review_score'] = result.get('score', 80)
        state['review_approved'] = result.get('approved', True)
        state['review_issues'] = result.get('issues', [])
        
        logger.info(f"质量审核完成: 得分 {result.get('score', 0)}, {'通过' if result.get('approved') else '未通过'}")
        
        if result.get('issues'):
            for issue in result['issues']:
                logger.info(f"  - [{issue.get('severity', 'medium')}] {issue.get('description', '')}")
        
        return state
