"""
可读性检测器 - 评估内容可读性

结合专业可读性指标（py-readability-metrics）和 LLM 分析
评估词汇、句法、篇章、表层特征四个维度
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas import ReadabilityResult, ContentIssue, ReadabilityLevel
from ..pipeline.readability_analyzer import get_readability_analyzer, ReadabilityMetrics

logger = logging.getLogger(__name__)


class ReadabilityChecker:
    """
    可读性检测器
    
    评估内容的可读性，包括词汇、句法、篇章、表层特征
    """
    
    def __init__(self, llm_service):
        """
        初始化可读性检测器
        
        Args:
            llm_service: LLM 服务实例
        """
        self.llm = llm_service
        self.pm = get_prompt_manager()
        self.analyzer = get_readability_analyzer()
    
    def check(self, content: str) -> ReadabilityResult:
        """
        检查内容可读性
        
        结合专业可读性指标和 LLM 分析
        
        Args:
            content: 待检查内容
            
        Returns:
            可读性评估结果
        """
        # 1. 先使用专业工具计算可读性指标
        metrics = self.analyzer.analyze(content)
        logger.info(f"专业可读性分析: score={metrics.overall_score}, level={metrics.difficulty_level}")
        
        # 2. 将指标信息传递给 LLM 进行综合分析
        prompt = self.pm.render_readability_check(content, metrics.to_dict())
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response:
                return self._default_result_with_metrics(metrics)
            
            return self._parse_response(response, metrics)
            
        except Exception as e:
            logger.error(f"可读性检测失败: {e}")
            return self._default_result_with_metrics(metrics)
    
    def _default_result_with_metrics(self, metrics: ReadabilityMetrics) -> ReadabilityResult:
        """基于专业指标返回默认结果"""
        level = ReadabilityLevel.NORMAL
        if metrics.difficulty_level == "easy":
            level = ReadabilityLevel.EASY
        elif metrics.difficulty_level == "hard":
            level = ReadabilityLevel.HARD
        elif metrics.difficulty_level == "expert":
            level = ReadabilityLevel.EXPERT
        
        # 构建摘要信息
        summary = f"可读性分析完成。平均句长: {metrics.avg_sentence_length:.0f}字, 建议阅读年级: {metrics.suggested_grade}"
        if metrics.summary:
            summary += f"。{metrics.summary}"
        
        return ReadabilityResult(
            score=metrics.overall_score,
            level=level,
            issues=[],
            summary=summary,
            vocabulary_score=metrics.overall_score,
            syntax_score=metrics.overall_score,
            discourse_score=metrics.overall_score,
            surface_score=metrics.overall_score,
        )
    
    def _parse_response(self, response: str, metrics: ReadabilityMetrics = None) -> ReadabilityResult:
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
            
            # 解析可读性等级
            level_str = data.get('level', 'normal')
            try:
                level = ReadabilityLevel(level_str)
            except ValueError:
                level = ReadabilityLevel.NORMAL
            
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
                ))
            
            # 如果有专业指标，优先使用专业指标的分数
            base_score = metrics.overall_score if metrics else 70
            
            return ReadabilityResult(
                score=int(data.get('score', base_score)),
                level=level,
                issues=issues,
                summary=data.get('summary', ''),
                vocabulary_score=int(data.get('vocabulary_score', base_score)),
                syntax_score=int(data.get('syntax_score', base_score)),
                discourse_score=int(data.get('discourse_score', base_score)),
                surface_score=int(data.get('surface_score', base_score)),
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析可读性检测结果失败: {e}")
            if metrics:
                return self._default_result_with_metrics(metrics)
            return self._default_result()
    
    def _default_result(self) -> ReadabilityResult:
        """返回默认结果"""
        return ReadabilityResult(
            score=70,
            level=ReadabilityLevel.NORMAL,
            issues=[],
            summary="可读性检测完成",
            vocabulary_score=70,
            syntax_score=70,
            discourse_score=70,
            surface_score=70,
        )
