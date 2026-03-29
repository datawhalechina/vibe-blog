"""
vibe-reviewer 数据模型定义
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ContentType(Enum):
    """内容类型"""
    TECHNICAL_TUTORIAL = "technical_tutorial"  # 技术教程
    SCIENCE_POPULAR = "science_popular"        # 科普文章
    NEWS = "news"                              # 新闻资讯
    OPINION = "opinion"                        # 观点评论
    DOCUMENTATION = "documentation"            # 技术文档
    UNKNOWN = "unknown"


class Severity(Enum):
    """问题严重度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(Enum):
    """问题类型"""
    # 深度问题
    VAGUE_CLAIM = "vague_claim"
    MISSING_DETAIL = "missing_detail"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    # 质量问题
    LOGIC_ERROR = "logic_error"
    LOGIC_GAP = "logic_gap"
    FACT_ERROR = "fact_error"
    OUTDATED_INFO = "outdated_info"
    MISSING_CONTENT = "missing_content"
    CONTRADICTION = "contradiction"
    # 可读性问题
    SENTENCE_TOO_LONG = "sentence_too_long"
    PARAGRAPH_TOO_LONG = "paragraph_too_long"
    JARGON_UNEXPLAINED = "jargon_unexplained"
    JARGON_DENSE = "jargon_dense"
    MISSING_TRANSITION = "missing_transition"
    POOR_STRUCTURE = "poor_structure"
    # 图片问题
    IMAGE_IRRELEVANT = "image_irrelevant"
    IMAGE_LOW_QUALITY = "image_low_quality"
    IMAGE_MISSING_ALT = "image_missing_alt"


class ReadabilityLevel(Enum):
    """可读性等级"""
    BEGINNER = "beginner"      # 入门级
    EASY = "easy"              # 易读
    NORMAL = "normal"          # 普通
    HARD = "hard"              # 较难
    OBSCURE = "obscure"        # 晦涩
    UNREADABLE = "unreadable"  # 不可读


class EvaluationStatus(Enum):
    """评估状态"""
    PENDING = "pending"
    CLONING = "cloning"
    SCANNING = "scanning"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


# ========== 请求/响应模型 ==========

@dataclass
class TutorialRequest:
    """添加教程请求"""
    git_url: str
    name: Optional[str] = None
    branch: str = "main"
    enable_search: bool = True
    max_search_rounds: int = 2


@dataclass
class TutorialResponse:
    """教程响应"""
    id: int
    name: str
    git_url: str
    status: str
    overall_score: float = 0
    total_chapters: int = 0
    total_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    created_at: str = ""
    last_evaluated: Optional[str] = None


# ========== 内容分析模型 ==========

@dataclass
class ContentSummary:
    """内容摘要"""
    topic: str                          # 文章主题
    content_type: ContentType           # 内容类型
    core_points: List[str]              # 核心观点列表
    key_terms: List[str]                # 关键术语
    fact_claims: List[str]              # 需要验证的事实声明
    search_queries: List[str]           # 生成的搜索查询


@dataclass
class SearchResult:
    """搜索结果"""
    query: str                          # 搜索查询
    source_url: str                     # 来源 URL
    title: str                          # 标题
    snippet: str                        # 摘要片段
    relevance_score: float = 0.0        # 相关性得分 0-1


@dataclass
class ReferenceContext:
    """参考资料上下文"""
    summary: ContentSummary             # 内容摘要
    search_results: List[SearchResult]  # 搜索结果列表
    verified_facts: List[Dict] = field(default_factory=list)
    contradictions: List[Dict] = field(default_factory=list)


# ========== 评估结果模型 ==========

@dataclass
class VaguePoint:
    """模糊点"""
    location: str                       # 问题位置
    issue: str                          # 问题描述
    question: str                       # 追问问题
    suggestion: str                     # 建议补充内容
    original_text: str = ""             # 原文文本（用于精确定位）


@dataclass
class ContentIssue:
    """内容问题"""
    issue_type: str                     # 问题类型
    severity: str                       # 严重度
    location: str                       # 问题位置
    description: str                    # 问题描述
    suggestion: str                     # 修改建议
    original_text: str = ""             # 原文文本（用于精确定位）
    reference: Optional[str] = None     # 参考资料来源
    category: str = ""                  # 问题分类（questioner/depth/quality/readability）


@dataclass
class DimensionScores:
    """多维度评分"""
    depth: int = 0                      # 深度得分 0-100
    accuracy: int = 0                   # 准确性得分
    completeness: int = 0               # 完整性得分
    logic: int = 0                      # 逻辑连贯性得分
    clarity: int = 0                    # 清晰度得分
    usefulness: int = 0                 # 实用价值得分
    novelty: int = 0                    # 新颖性得分
    readability: int = 0                # 可读性得分


@dataclass
class ActionableFeedback:
    """可操作反馈"""
    priority: int                       # 优先级 1-5, 1最高
    location: str                       # 具体位置
    issue_type: str                     # 问题类型
    problem: str                        # 具体问题描述
    action: str                         # 具体修改方案
    reference: Optional[str] = None     # 参考资料来源
    estimated_effort: str = "medium"    # 预估工作量 low|medium|high


@dataclass
class DepthCheckResult:
    """深度检查结果"""
    score: int                          # 深度得分 0-100
    is_detailed_enough: bool
    vague_points: List[VaguePoint]
    summary: str


@dataclass
class QualityReviewResult:
    """质量审核结果"""
    score: int                          # 质量得分 0-100
    approved: bool
    issues: List[ContentIssue]
    summary: str
    # 子维度得分
    logic_score: int = 0
    accuracy_score: int = 0
    completeness_score: int = 0


@dataclass
class ReadabilityResult:
    """可读性评估结果"""
    score: int                          # 可读性得分 0-100
    level: ReadabilityLevel             # 可读性等级
    issues: List[ContentIssue]
    summary: str
    # 子维度得分
    vocabulary_score: int = 0
    syntax_score: int = 0
    discourse_score: int = 0
    surface_score: int = 0


@dataclass
class ChapterEvaluationResult:
    """章节评估结果"""
    chapter_id: int
    file_path: str
    title: str
    overall_score: int
    dimension_scores: DimensionScores
    depth_result: DepthCheckResult
    quality_result: QualityReviewResult
    readability_result: ReadabilityResult
    actionable_feedback: List[ActionableFeedback]
    references: List[SearchResult]


@dataclass
class ImageAnalysisResult:
    """图片分析结果"""
    image_path: str
    description: str                    # 图片内容描述
    detected_text: Optional[str]        # OCR 检测到的文字
    image_type: str                     # screenshot|diagram|chart|photo|code
    relevance_score: float              # 与上下文的相关性 0-1
    quality_score: int                  # 图片质量得分 0-100
    issues: List[ContentIssue]
