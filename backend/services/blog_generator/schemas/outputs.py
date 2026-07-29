"""Stable Pydantic models for structured Agent outputs."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SectionOutline(BaseModel):
    """章节大纲"""
    id: str
    title: str
    key_concept: str
    content_outline: List[str] = Field(default_factory=list)
    image_type: Literal["flowchart", "architecture", "sequence", "comparison", "chart", "none"] = "none"
    image_description: str = ""
    code_blocks: int = 0
    has_output_block: bool = False
    key_quote: str = ""


class BlogOutline(BaseModel):
    """博客大纲"""
    title: str
    subtitle: str
    reading_time: int
    article_type: Literal["problem-solution", "tutorial", "comparison"]
    introduction: str
    core_value: str
    table_of_contents: List[str] = Field(default_factory=list)
    sections: List[SectionOutline] = Field(default_factory=list)
    conclusion_summary_points: List[str] = Field(default_factory=list)
    conclusion_next_steps: str = ""
    reference_links: List[str] = Field(default_factory=list)


class SectionContent(BaseModel):
    """章节内容"""
    id: str
    title: str
    content: str
    image_ids: List[str] = Field(default_factory=list)
    code_ids: List[str] = Field(default_factory=list)


class CodeBlock(BaseModel):
    """代码块"""
    id: str
    code: str
    output: str
    explanation: str
    language: str = "python"


class ImageResource(BaseModel):
    """图片资源"""
    id: str
    render_method: Literal["mermaid", "ai_image", "matplotlib"]
    content: str
    rendered_path: Optional[str] = None
    caption: str


class VaguePoint(BaseModel):
    """模糊点 (Questioner 输出)"""
    location: str
    issue: str
    question: str
    suggestion: str


class QuestionResult(BaseModel):
    """追问结果"""
    section_id: str
    is_detailed_enough: bool
    vague_points: List[VaguePoint] = Field(default_factory=list)
    depth_score: int


class ReviewIssue(BaseModel):
    """审核问题"""
    section_id: str
    issue_type: Literal["completeness", "logic", "verbatim_violation", "learning_objective_gap"]
    severity: Literal["high", "medium", "low"]
    description: str
    suggestion: str
    original_value: Optional[str] = None
    found_value: Optional[str] = None


class LearningObjective(BaseModel):
    """学习目标"""
    type: Literal["primary", "secondary", "tertiary"]
    objective: str


class AudienceAnalysis(BaseModel):
    """受众分析"""
    knowledge_level: Literal["beginner", "intermediate", "advanced"]
    reading_purpose: str
    expected_outcome: str


class VerbatimDataItem(BaseModel):
    """Verbatim 数据项（需要原样保留的数据）"""
    type: Literal["statistic", "quote", "term"]
    value: str
    context: Optional[str] = None
    source: Optional[str] = None
    definition: Optional[str] = None


class InstructionalAnalysis(BaseModel):
    """教学设计分析（Researcher 输出）"""
    learning_objectives: List[LearningObjective] = Field(default_factory=list)
    audience: Optional[AudienceAnalysis] = None
    content_type: Literal["tutorial", "concept", "comparison", "problem-solving", "overview"] = "tutorial"
    verbatim_data: List[VerbatimDataItem] = Field(default_factory=list)


class InformationArchitecture(BaseModel):
    """信息架构（Planner 输出）"""
    structure_type: Literal["linear-progression", "hierarchical", "comparison", "problem-solving"]
    learning_objectives_mapping: List[dict] = Field(default_factory=list)


class SearchResult(BaseModel):
    """搜索结果"""
    title: str
    url: str
    content: str
    source: str = ""
    publish_date: str = ""
    relevance_score: float = 0.0


class KnowledgeGap(BaseModel):
    """知识空白点"""
    gap_type: Literal["missing_data", "vague_concept", "no_example"]
    description: str
    suggested_query: str
    section_id: Optional[str] = None


class SearchHistoryItem(BaseModel):
    """搜索历史记录"""
    round: int
    queries: List[str]
    results_count: int
    gaps_addressed: List[str]


__all__ = [
    "AudienceAnalysis",
    "BlogOutline",
    "CodeBlock",
    "ImageResource",
    "InformationArchitecture",
    "InstructionalAnalysis",
    "KnowledgeGap",
    "LearningObjective",
    "QuestionResult",
    "ReviewIssue",
    "SearchHistoryItem",
    "SearchResult",
    "SectionContent",
    "SectionOutline",
    "VaguePoint",
    "VerbatimDataItem",
]
