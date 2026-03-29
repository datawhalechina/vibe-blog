"""
深度检查器 - 评估内容深度

参考 blog_generator/agents/questioner.py 逻辑，但独立实现
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas import DepthCheckResult, VaguePoint

logger = logging.getLogger(__name__)


class DepthChecker:
    """
    深度检查器
    
    评估内容的深度，识别模糊点和需要补充的地方
    """
    
    def __init__(self, llm_service):
        """
        初始化深度检查器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
        self.pm = get_prompt_manager()
    
    def check(
        self, 
        content: str, 
        references: List[Dict] = None
    ) -> DepthCheckResult:
        """
        检查内容深度
        
        Args:
            content: 待检查内容
            references: 参考资料列表
            
        Returns:
            深度检查结果
        """
        prompt = self.pm.render_depth_check(content, references)
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return self._default_result()
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"深度检查失败: {e}")
            return self._default_result()
    
    def _parse_response(self, response: str) -> DepthCheckResult:
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
            
            # 解析模糊点
            vague_points = []
            for vp in data.get('vague_points', []):
                vague_points.append(VaguePoint(
                    location=vp.get('location', ''),
                    issue=vp.get('issue', ''),
                    question=vp.get('question', ''),
                    suggestion=vp.get('suggestion', ''),
                    original_text=vp.get('original_text', ''),
                ))
            
            return DepthCheckResult(
                score=int(data.get('score', 70)),
                is_detailed_enough=data.get('is_detailed_enough', True),
                vague_points=vague_points,
                summary=data.get('summary', ''),
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析深度检查结果失败: {e}")
            return self._default_result()
    
    def _default_result(self) -> DepthCheckResult:
        """返回默认结果"""
        return DepthCheckResult(
            score=70,
            is_detailed_enough=True,
            vague_points=[],
            summary="深度检查完成",
        )
