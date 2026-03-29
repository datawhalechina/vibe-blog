"""
追问检查器 - 发现内容模糊点并生成优化建议

参考 blog_generator/agents/questioner.py 逻辑，但专注于生成优化建议而非深化内容
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas import ContentIssue

logger = logging.getLogger(__name__)


class Questioner:
    """
    追问检查器
    
    通过追问发现内容中的模糊点、遗漏点，并转换为优化建议
    """
    
    def __init__(self, llm_service):
        """
        初始化追问检查器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
        self.pm = get_prompt_manager()
    
    def question(
        self, 
        content: str,
        content_type: str = "tutorial",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        对内容进行追问检查
        
        Args:
            content: 待检查内容（整篇文档）
            content_type: 内容类型（tutorial/blog/outline）
            context: 上下文信息（前后章节摘要）
            
        Returns:
            追问结果，包含模糊点和优化建议
        """
        prompt = self.pm.render_questioner(content, content_type, context)
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return self._default_result()
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"追问检查失败: {e}")
            return self._default_result()
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
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
            
            # 解析模糊点并转换为问题
            vague_points = data.get('vague_points', [])
            issues = []
            
            for vp in vague_points:
                # 将追问的模糊点转换为 ContentIssue 格式
                issue = ContentIssue(
                    issue_type=vp.get('issue_type', 'vague_claim'),
                    severity=self._determine_severity(vp),
                    location=vp.get('location', ''),
                    original_text=vp.get('original_text', ''),
                    description=vp.get('issue', vp.get('description', '')),
                    suggestion=vp.get('suggestion', ''),
                    category='depth',  # 追问产生的问题归类为深度问题
                )
                issues.append(issue)
            
            return {
                'score': int(data.get('depth_score', data.get('score', 70))),
                'is_detailed_enough': data.get('is_detailed_enough', True),
                'issues': issues,
                'summary': data.get('summary', ''),
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析追问结果失败: {e}")
            return self._default_result()
    
    def _determine_severity(self, vague_point: Dict) -> str:
        """根据模糊点类型确定严重程度"""
        issue_type = vague_point.get('issue_type', '')
        
        # 高严重度：核心概念模糊、关键步骤缺失
        if issue_type in ['missing_step', 'core_concept_vague', 'no_example']:
            return 'high'
        # 中严重度：解释不足、缺少细节
        elif issue_type in ['insufficient_explanation', 'missing_detail', 'vague_claim']:
            return 'medium'
        # 低严重度：可选优化
        else:
            return 'low'
    
    def _default_result(self) -> Dict[str, Any]:
        """返回默认结果"""
        return {
            'score': 70,
            'is_detailed_enough': True,
            'issues': [],
            'summary': '追问检查完成',
        }
    
    def convert_to_issues(self, question_result: Dict[str, Any]) -> List[ContentIssue]:
        """
        将追问结果转换为问题列表
        
        Args:
            question_result: 追问检查结果
            
        Returns:
            问题列表
        """
        return question_result.get('issues', [])
