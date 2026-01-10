"""
中文技术博客可读性分析器

专门针对中文技术博客的可读性评估，使用以下指标：
1. 平均句长 (ASL) - 中文最佳句长 15-25 字
2. 长句比例 - 超过 40 字的句子占比
3. 段落结构 - 是否有合理分段
4. 术语密度 - 专业术语的使用频率
5. 结构化程度 - 标题、列表、代码块的使用

参考: python-readability-cn 的思路，但针对技术博客优化
"""
import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 尝试导入 jieba 分词
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，将使用简化的中文分析")


@dataclass
class ReadabilityMetrics:
    """中文可读性指标"""
    # 基础统计
    char_count: int = 0           # 中文字符数
    word_count: int = 0           # 分词后词数
    sentence_count: int = 0       # 句子数
    paragraph_count: int = 0      # 段落数
    
    # 句子指标
    avg_sentence_length: float = 0.0      # 平均句长（字符）
    long_sentence_ratio: float = 0.0      # 长句比例（>40字）
    very_long_sentence_ratio: float = 0.0 # 超长句比例（>60字）
    
    # 段落指标
    avg_paragraph_length: float = 0.0     # 平均段落长度
    
    # 结构指标
    heading_count: int = 0        # 标题数量
    list_count: int = 0           # 列表项数量
    code_block_count: int = 0     # 代码块数量
    has_structure: bool = False   # 是否有良好结构
    
    # 综合评分 (0-100)
    overall_score: int = 70
    # 难度等级
    difficulty_level: str = "normal"  # easy, normal, hard, expert
    # 建议阅读年级
    suggested_grade: str = ""
    # 评估摘要
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'char_count': self.char_count,
            'word_count': self.word_count,
            'sentence_count': self.sentence_count,
            'paragraph_count': self.paragraph_count,
            'avg_sentence_length': round(self.avg_sentence_length, 1),
            'long_sentence_ratio': round(self.long_sentence_ratio * 100, 1),
            'very_long_sentence_ratio': round(self.very_long_sentence_ratio * 100, 1),
            'avg_paragraph_length': round(self.avg_paragraph_length, 1),
            'heading_count': self.heading_count,
            'list_count': self.list_count,
            'code_block_count': self.code_block_count,
            'has_structure': self.has_structure,
            'overall_score': self.overall_score,
            'difficulty_level': self.difficulty_level,
            'suggested_grade': self.suggested_grade,
            'summary': self.summary,
        }


class ReadabilityAnalyzer:
    """
    中文技术博客可读性分析器
    
    评估维度：
    1. 句子可读性 (40%) - 句长、长句比例
    2. 段落结构 (20%) - 段落划分、段落长度
    3. 文档结构 (20%) - 标题、列表、代码块
    4. 整体流畅度 (20%) - 综合评估
    """
    
    def __init__(self):
        self.jieba_available = JIEBA_AVAILABLE
        if self.jieba_available:
            # 静默加载 jieba
            jieba.setLogLevel(logging.WARNING)
    
    def analyze(self, text: str) -> ReadabilityMetrics:
        """
        分析文本可读性
        
        Args:
            text: 待分析的 Markdown 文本
            
        Returns:
            可读性指标
        """
        metrics = ReadabilityMetrics()
        
        if not text or len(text.strip()) < 50:
            metrics.summary = "文本过短，无法进行有效分析"
            return metrics
        
        # 1. 提取结构信息（在清理前）
        self._extract_structure(text, metrics)
        
        # 2. 清理 Markdown 语法
        clean_text = self._clean_markdown(text)
        
        # 3. 基础统计
        self._basic_stats(clean_text, metrics)
        
        # 4. 句子分析
        self._sentence_analysis(clean_text, metrics)
        
        # 5. 段落分析
        self._paragraph_analysis(clean_text, metrics)
        
        # 6. 计算综合评分
        self._calculate_score(metrics)
        
        return metrics
    
    def _extract_structure(self, text: str, metrics: ReadabilityMetrics):
        """提取文档结构信息"""
        # 标题数量
        metrics.heading_count = len(re.findall(r'^#{1,6}\s+', text, re.MULTILINE))
        
        # 列表项数量
        metrics.list_count = len(re.findall(r'^[\s]*[-*+]\s+', text, re.MULTILINE))
        metrics.list_count += len(re.findall(r'^[\s]*\d+\.\s+', text, re.MULTILINE))
        
        # 代码块数量
        metrics.code_block_count = len(re.findall(r'```', text)) // 2
        
        # 判断是否有良好结构
        metrics.has_structure = (
            metrics.heading_count >= 2 or 
            metrics.list_count >= 3 or 
            metrics.code_block_count >= 1
        )
    
    def _clean_markdown(self, text: str) -> str:
        """清理 Markdown 语法，保留纯文本"""
        # 移除代码块
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
        
        # 移除 YAML front matter
        text = re.sub(r'^---[\s\S]*?---', '', text)
        
        # 移除链接，保留文字
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 移除图片
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除标题标记
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # 移除强调标记
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # 移除列表标记
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # 移除引用标记
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        
        # 移除表格
        text = re.sub(r'\|[^\n]+\|', '', text)
        text = re.sub(r'^[-|:\s]+$', '', text, flags=re.MULTILINE)
        
        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _basic_stats(self, text: str, metrics: ReadabilityMetrics):
        """基础统计"""
        # 中文字符数
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        metrics.char_count = len(chinese_chars)
        
        # 分词统计
        if self.jieba_available and metrics.char_count > 0:
            words = list(jieba.cut(text))
            # 过滤空白和标点
            words = [w for w in words if w.strip() and not re.match(r'^[\s\W]+$', w)]
            metrics.word_count = len(words)
        else:
            # 简单估算：中文约 1.5 字/词
            metrics.word_count = max(1, metrics.char_count // 2)
    
    def _sentence_analysis(self, text: str, metrics: ReadabilityMetrics):
        """句子分析"""
        # 按中文句号、问号、感叹号分句
        sentences = re.split(r'[。！？!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        
        metrics.sentence_count = len(sentences)
        
        if metrics.sentence_count == 0:
            return
        
        # 计算每句的中文字符数
        sentence_lengths = []
        long_count = 0
        very_long_count = 0
        
        for s in sentences:
            # 只统计中文字符
            chinese_len = len(re.findall(r'[\u4e00-\u9fff]', s))
            sentence_lengths.append(chinese_len)
            
            if chinese_len > 40:
                long_count += 1
            if chinese_len > 60:
                very_long_count += 1
        
        # 平均句长
        metrics.avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
        
        # 长句比例
        metrics.long_sentence_ratio = long_count / metrics.sentence_count
        metrics.very_long_sentence_ratio = very_long_count / metrics.sentence_count
    
    def _paragraph_analysis(self, text: str, metrics: ReadabilityMetrics):
        """段落分析"""
        # 按空行分段
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
        
        metrics.paragraph_count = len(paragraphs)
        
        if metrics.paragraph_count == 0:
            return
        
        # 计算平均段落长度（中文字符）
        para_lengths = [len(re.findall(r'[\u4e00-\u9fff]', p)) for p in paragraphs]
        metrics.avg_paragraph_length = sum(para_lengths) / len(para_lengths)
    
    def _calculate_score(self, metrics: ReadabilityMetrics):
        """
        计算综合可读性评分
        
        评分标准（满分100）：
        1. 句子可读性 (40分)
           - 平均句长 15-25 字最佳
           - 长句比例 < 20% 最佳
        2. 段落结构 (20分)
           - 有合理分段
           - 段落长度适中
        3. 文档结构 (20分)
           - 有标题层级
           - 有列表辅助
        4. 整体流畅度 (20分)
           - 综合评估
        """
        score = 0
        
        # 1. 句子可读性 (40分)
        sentence_score = 40
        
        # 平均句长评分
        asl = metrics.avg_sentence_length
        if asl <= 0:
            sentence_score = 20
        elif asl <= 20:
            sentence_score = 40  # 最佳
        elif asl <= 30:
            sentence_score = 40 - (asl - 20) * 1  # 每超1字扣1分
        elif asl <= 40:
            sentence_score = 30 - (asl - 30) * 1
        elif asl <= 50:
            sentence_score = 20 - (asl - 40) * 0.5
        else:
            sentence_score = 15
        
        # 长句比例扣分
        if metrics.long_sentence_ratio > 0.3:
            sentence_score -= 10
        elif metrics.long_sentence_ratio > 0.2:
            sentence_score -= 5
        
        score += max(0, sentence_score)
        
        # 2. 段落结构 (20分)
        para_score = 20
        
        if metrics.paragraph_count < 2:
            para_score = 10  # 没有分段
        elif metrics.avg_paragraph_length > 300:
            para_score = 12  # 段落过长
        elif metrics.avg_paragraph_length > 200:
            para_score = 16
        
        score += para_score
        
        # 3. 文档结构 (20分)
        structure_score = 10  # 基础分
        
        if metrics.heading_count >= 3:
            structure_score += 5
        elif metrics.heading_count >= 1:
            structure_score += 3
        
        if metrics.list_count >= 3:
            structure_score += 3
        elif metrics.list_count >= 1:
            structure_score += 1
        
        if metrics.code_block_count >= 1:
            structure_score += 2  # 技术博客有代码是好事
        
        score += min(20, structure_score)
        
        # 4. 整体流畅度 (20分) - 基于综合因素
        fluency_score = 15  # 基础分
        
        if metrics.has_structure:
            fluency_score += 3
        if metrics.sentence_count >= 5:
            fluency_score += 2
        
        score += min(20, fluency_score)
        
        # 最终评分
        metrics.overall_score = max(0, min(100, int(score)))
        
        # 设置难度等级和建议
        self._set_difficulty_level(metrics)
        self._generate_summary(metrics)
    
    def _set_difficulty_level(self, metrics: ReadabilityMetrics):
        """设置难度等级"""
        score = metrics.overall_score
        
        if score >= 85:
            metrics.difficulty_level = "easy"
            metrics.suggested_grade = "初中及以上"
        elif score >= 70:
            metrics.difficulty_level = "normal"
            metrics.suggested_grade = "高中及以上"
        elif score >= 55:
            metrics.difficulty_level = "hard"
            metrics.suggested_grade = "大学及以上"
        else:
            metrics.difficulty_level = "expert"
            metrics.suggested_grade = "专业人士"
    
    def _generate_summary(self, metrics: ReadabilityMetrics):
        """生成评估摘要"""
        issues = []
        
        if metrics.avg_sentence_length > 35:
            issues.append(f"平均句长 {metrics.avg_sentence_length:.0f} 字偏长，建议控制在 25 字以内")
        
        if metrics.long_sentence_ratio > 0.25:
            issues.append(f"长句比例 {metrics.long_sentence_ratio*100:.0f}% 偏高，建议拆分长句")
        
        if metrics.paragraph_count < 3 and metrics.char_count > 500:
            issues.append("段落划分不足，建议增加分段")
        
        if not metrics.has_structure:
            issues.append("缺少结构化元素（标题/列表），建议添加")
        
        if issues:
            metrics.summary = "；".join(issues)
        else:
            metrics.summary = "可读性良好，结构清晰"


# 全局实例
_analyzer: Optional[ReadabilityAnalyzer] = None


def get_readability_analyzer() -> ReadabilityAnalyzer:
    """获取可读性分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ReadabilityAnalyzer()
    return _analyzer
