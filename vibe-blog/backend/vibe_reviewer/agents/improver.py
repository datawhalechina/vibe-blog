"""
改进建议生成器 - 生成可操作的反馈

参考 Agentic Reviewer 的设计理念，生成优先级排序的具体改进建议
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas import ActionableFeedback, DepthCheckResult, QualityReviewResult, ReadabilityResult

logger = logging.getLogger(__name__)


class Improver:
    """
    改进建议生成器
    
    根据评估结果生成可操作的改进建议
    """
    
    def __init__(self, llm_service):
        """
        初始化改进建议生成器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
        self.pm = get_prompt_manager()
    
    def generate(
        self,
        content: str,
        depth_result: DepthCheckResult,
        quality_result: QualityReviewResult,
        readability_result: ReadabilityResult,
    ) -> List[ActionableFeedback]:
        """
        生成改进建议
        
        Args:
            content: 原始内容
            depth_result: 深度检查结果
            quality_result: 质量审核结果
            readability_result: 可读性评估结果
            
        Returns:
            改进建议列表
        """
        # 转换为字典格式
        depth_dict = {
            'score': depth_result.score,
            'vague_points': [
                {'location': vp.location, 'issue': vp.issue, 'question': vp.question, 'suggestion': vp.suggestion}
                for vp in depth_result.vague_points
            ]
        }
        
        quality_dict = {
            'score': quality_result.score,
            'issues': [
                {'issue_type': i.issue_type, 'severity': i.severity, 'location': i.location, 
                 'description': i.description, 'suggestion': i.suggestion}
                for i in quality_result.issues
            ]
        }
        
        readability_dict = {
            'score': readability_result.score,
            'level': readability_result.level.value,
            'issues': [
                {'issue_type': i.issue_type, 'severity': i.severity, 'location': i.location,
                 'description': i.description, 'suggestion': i.suggestion}
                for i in readability_result.issues
            ]
        }
        
        prompt = self.pm.render_improvement(
            content=content,
            depth_result=depth_dict,
            quality_result=quality_dict,
            readability_result=readability_dict,
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return self._generate_from_results(depth_result, quality_result, readability_result)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"生成改进建议失败: {e}")
            return self._generate_from_results(depth_result, quality_result, readability_result)
    
    def _parse_response(self, response: str) -> List[ActionableFeedback]:
        """解析 LLM 响应"""
        try:
            # 提取 JSON
            response = response.strip()
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                response = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                response = response[start:end].strip()
            
            data = json.loads(response)
            
            feedback_list = []
            for fb in data.get('feedback', []):
                feedback_list.append(ActionableFeedback(
                    priority=int(fb.get('priority', 3)),
                    location=fb.get('location', ''),
                    issue_type=fb.get('issue_type', 'unknown'),
                    problem=fb.get('problem', ''),
                    action=fb.get('action', ''),
                    reference=fb.get('reference'),
                    estimated_effort=fb.get('estimated_effort', 'medium'),
                ))
            
            # 按优先级排序
            feedback_list.sort(key=lambda x: x.priority)
            
            return feedback_list
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析改进建议失败: {e}")
            return []
    
    def _generate_from_results(
        self,
        depth_result: DepthCheckResult,
        quality_result: QualityReviewResult,
        readability_result: ReadabilityResult,
    ) -> List[ActionableFeedback]:
        """从评估结果直接生成改进建议 (备用方案)"""
        feedback_list = []
        
        # 从深度检查结果生成
        for vp in depth_result.vague_points:
            feedback_list.append(ActionableFeedback(
                priority=3,
                location=vp.location,
                issue_type='missing_detail',
                problem=vp.issue,
                action=vp.suggestion,
                estimated_effort='medium',
            ))
        
        # 从质量审核结果生成
        for issue in quality_result.issues:
            priority = 1 if issue.severity == 'high' else (2 if issue.severity == 'medium' else 4)
            feedback_list.append(ActionableFeedback(
                priority=priority,
                location=issue.location,
                issue_type=issue.issue_type,
                problem=issue.description,
                action=issue.suggestion,
                reference=issue.reference,
                estimated_effort='medium' if issue.severity != 'low' else 'low',
            ))
        
        # 从可读性结果生成
        for issue in readability_result.issues:
            priority = 2 if issue.severity == 'high' else (3 if issue.severity == 'medium' else 4)
            feedback_list.append(ActionableFeedback(
                priority=priority,
                location=issue.location,
                issue_type=issue.issue_type,
                problem=issue.description,
                action=issue.suggestion,
                estimated_effort='low',
            ))
        
        # 按优先级排序
        feedback_list.sort(key=lambda x: x.priority)
        
        return feedback_list
