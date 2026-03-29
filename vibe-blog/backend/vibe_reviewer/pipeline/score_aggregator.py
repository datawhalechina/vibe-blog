"""
分数聚合器 - 多维度评分合成

参考 Agentic Reviewer 的加权合成策略
"""
import logging
from typing import Dict, Any

from ..schemas import (
    DimensionScores, 
    DepthCheckResult, 
    QualityReviewResult, 
    ReadabilityResult,
    ContentType,
)

logger = logging.getLogger(__name__)


# 不同内容类型的权重配置
WEIGHT_CONFIGS = {
    ContentType.TECHNICAL_TUTORIAL: {
        'depth': 0.25,
        'accuracy': 0.25,
        'completeness': 0.15,
        'logic': 0.15,
        'readability': 0.20,
    },
    ContentType.SCIENCE_POPULAR: {
        'depth': 0.15,
        'accuracy': 0.20,
        'completeness': 0.15,
        'logic': 0.15,
        'readability': 0.35,
    },
    ContentType.DOCUMENTATION: {
        'depth': 0.20,
        'accuracy': 0.30,
        'completeness': 0.25,
        'logic': 0.15,
        'readability': 0.10,
    },
    ContentType.NEWS: {
        'depth': 0.10,
        'accuracy': 0.35,
        'completeness': 0.20,
        'logic': 0.15,
        'readability': 0.20,
    },
    ContentType.OPINION: {
        'depth': 0.20,
        'accuracy': 0.15,
        'completeness': 0.15,
        'logic': 0.30,
        'readability': 0.20,
    },
    ContentType.UNKNOWN: {
        'depth': 0.20,
        'accuracy': 0.20,
        'completeness': 0.20,
        'logic': 0.20,
        'readability': 0.20,
    },
}


class ScoreAggregator:
    """
    分数聚合器
    
    将多维度评分合成为最终分数
    """
    
    def __init__(self, custom_weights: Dict[str, float] = None):
        """
        初始化分数聚合器
        
        Args:
            custom_weights: 自定义权重配置
        """
        self.custom_weights = custom_weights
    
    def aggregate(
        self,
        depth_result: DepthCheckResult,
        quality_result: QualityReviewResult,
        readability_result: ReadabilityResult,
        content_type: ContentType = ContentType.UNKNOWN,
    ) -> tuple:
        """
        聚合评分
        
        Args:
            depth_result: 深度检查结果
            quality_result: 质量审核结果
            readability_result: 可读性评估结果
            content_type: 内容类型
            
        Returns:
            (overall_score, dimension_scores)
        """
        # 获取权重配置
        weights = self.custom_weights or WEIGHT_CONFIGS.get(
            content_type, WEIGHT_CONFIGS[ContentType.UNKNOWN]
        )
        
        # 构建维度分数
        dimension_scores = DimensionScores(
            depth=depth_result.score,
            accuracy=quality_result.accuracy_score,
            completeness=quality_result.completeness_score,
            logic=quality_result.logic_score,
            clarity=readability_result.vocabulary_score,
            usefulness=0,  # 暂不评估
            novelty=0,     # 暂不评估
            readability=readability_result.score,
        )
        
        # 计算加权总分
        overall_score = (
            weights.get('depth', 0.2) * depth_result.score +
            weights.get('accuracy', 0.2) * quality_result.accuracy_score +
            weights.get('completeness', 0.2) * quality_result.completeness_score +
            weights.get('logic', 0.2) * quality_result.logic_score +
            weights.get('readability', 0.2) * readability_result.score
        )
        
        return int(overall_score), dimension_scores
    
    def get_grade(self, score: int) -> str:
        """
        根据分数获取等级
        
        Args:
            score: 分数 0-100
            
        Returns:
            等级 A/B/C/D/F
        """
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def get_summary(
        self,
        overall_score: int,
        dimension_scores: DimensionScores,
        issue_count: int,
    ) -> str:
        """
        生成评分摘要
        
        Args:
            overall_score: 总分
            dimension_scores: 维度分数
            issue_count: 问题数量
            
        Returns:
            摘要文本
        """
        grade = self.get_grade(overall_score)
        
        # 找出最弱的维度
        dimensions = {
            '深度': dimension_scores.depth,
            '准确性': dimension_scores.accuracy,
            '完整性': dimension_scores.completeness,
            '逻辑性': dimension_scores.logic,
            '可读性': dimension_scores.readability,
        }
        
        weakest = min(dimensions.items(), key=lambda x: x[1])
        strongest = max(dimensions.items(), key=lambda x: x[1])
        
        summary = f"综合评分 {overall_score} 分 ({grade}级)。"
        
        if issue_count > 0:
            summary += f"共发现 {issue_count} 个问题。"
        
        if weakest[1] < 70:
            summary += f"建议重点改进{weakest[0]}方面。"
        elif strongest[1] >= 85:
            summary += f"{strongest[0]}方面表现优秀。"
        
        return summary
