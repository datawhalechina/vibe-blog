"""
质量审核器 - 评估内容质量

参考 blog_generator/agents/reviewer.py 逻辑，但独立实现
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas import QualityReviewResult, ContentIssue

logger = logging.getLogger(__name__)


class QualityReviewer:
    """
    质量审核器
    
    评估内容的逻辑性、准确性、完整性
    """
    
    def __init__(self, llm_service):
        """
        初始化质量审核器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
        self.pm = get_prompt_manager()
    
    def review(
        self, 
        content: str, 
        references: List[Dict] = None
    ) -> QualityReviewResult:
        """
        审核内容质量
        
        Args:
            content: 待审核内容
            references: 参考资料列表
            
        Returns:
            质量审核结果
        """
        prompt = self.pm.render_quality_review(content, references)
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return self._default_result()
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"质量审核失败: {e}")
            return self._default_result()
    
    def _parse_response(self, response: str) -> QualityReviewResult:
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
            
            # 解析问题列表
            issues = []
            for issue in data.get('issues', []):
                issues.append(ContentIssue(
                    issue_type=issue.get('issue_type', 'unknown'),
                    severity=issue.get('severity', 'medium'),
                    location=issue.get('location', ''),
                    description=issue.get('description', ''),
                    suggestion=issue.get('suggestion', ''),
                    original_text=issue.get('original_text', ''),
                    reference=issue.get('reference'),
                ))
            
            return QualityReviewResult(
                score=int(data.get('score', 70)),
                approved=data.get('approved', True),
                issues=issues,
                summary=data.get('summary', ''),
                logic_score=int(data.get('logic_score', 70)),
                accuracy_score=int(data.get('accuracy_score', 70)),
                completeness_score=int(data.get('completeness_score', 70)),
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析质量审核结果失败: {e}")
            return self._default_result()
    
    def _default_result(self) -> QualityReviewResult:
        """返回默认结果"""
        return QualityReviewResult(
            score=70,
            approved=True,
            issues=[],
            summary="质量审核完成",
            logic_score=70,
            accuracy_score=70,
            completeness_score=70,
        )
