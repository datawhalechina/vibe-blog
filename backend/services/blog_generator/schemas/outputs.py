"""Stable Pydantic models for structured Agent outputs."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


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


class ArtistGenerationOutput(BaseModel):
    render_method: Literal["mermaid", "ai_image", "matplotlib"]
    content: str
    caption: str
    style_description: str = ""


class ContentEvaluationOutput(BaseModel):
    scores: Dict[str, float]
    overall_quality: Optional[float] = None
    specific_issues: List[str]
    improvement_suggestions: List[str]


class MissingDiagram(BaseModel):
    location: str = ""
    diagram_type: str
    description: str
    context: str


class MissingDiagramsOutput(BaseModel):
    needs_diagrams: List[MissingDiagram]


class FactCheckClaim(BaseModel):
    id: int
    text: str
    sid: str
    v: Literal["S", "C", "U"]


class FactCheckFix(BaseModel):
    sid: str
    old: str
    new: str


class FactCheckOutput(BaseModel):
    score: int = Field(ge=1, le=5)
    claims: List[FactCheckClaim]
    fixes: List[FactCheckFix]


class HumanizerScoreValues(BaseModel):
    directness: int = Field(ge=1, le=10)
    rhythm: int = Field(ge=1, le=10)
    trust: int = Field(ge=1, le=10)
    authenticity: int = Field(ge=1, le=10)
    conciseness: int = Field(ge=1, le=10)
    total: int = Field(ge=5, le=50)


class HumanizerScoreOutput(BaseModel):
    score: HumanizerScoreValues
    issues_summary: str


class TextReplacement(BaseModel):
    old: str
    new: str


class HumanizerRewriteOutput(BaseModel):
    replacements: List[TextReplacement]


class ReviewerOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    approved: Optional[bool] = None
    issues: List[ReviewIssue]
    summary: str


class SummaryOutput(BaseModel):
    tldr: str
    seo_keywords: List[str]
    social_summary: str
    meta_description: str


class ConsistencyIssue(BaseModel):
    check_type: str
    severity: Literal["high", "medium", "low"]
    section_id: str
    description: str
    suggestion: str


class ThreadCheckOutput(BaseModel):
    overall_coherence: int = Field(ge=1, le=5)
    issues: List[ConsistencyIssue]
    summary: str


class VoiceProfile(BaseModel):
    target_tone: str
    target_formality: str
    target_person: str


class ChapterVoice(BaseModel):
    section_id: str
    tone: str
    formality: str
    dominant_person: str


class VoiceCheckOutput(BaseModel):
    voice_profile: VoiceProfile
    chapter_voice_map: List[ChapterVoice]
    issues: List[ConsistencyIssue]
    summary: str


class CodeGenerationOutput(BaseModel):
    code_block: str
    output_block: str
    explanation: str


class DepthVaguePoint(BaseModel):
    location: str
    question: str
    suggestion: str


class DepthCheckOutput(BaseModel):
    is_detailed_enough: bool
    depth_score: int = Field(ge=0, le=100)
    vague_points: List[DepthVaguePoint]


class PlannerSectionOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    title: str
    key_concept: str = ""
    content_outline: List[str] = Field(default_factory=list)
    assigned_materials: List[Dict[str, Any]] = Field(default_factory=list)
    subsections: List[Dict[str, Any]] = Field(default_factory=list)


class PlannerOutlineOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    sections: List[PlannerSectionOutput]


class KeyConceptOutput(BaseModel):
    name: str
    description: str


class ReferenceOutput(BaseModel):
    title: str
    url: str
    relevance: str = ""


class ResearchSummaryOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    background_knowledge: str = ""
    key_concepts: List[KeyConceptOutput | str] = Field(default_factory=list)
    top_references: List[ReferenceOutput] = Field(default_factory=list)
    instructional_analysis: Optional[InstructionalAnalysis] = None


class DistilledSourceOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    url: str
    core_insight: str
    key_data: List[str]
    unique_perspective: str
    content_type: str
    credibility: str
    relevance_score: float


class MaterialByTypeOutput(BaseModel):
    concepts: List[str]
    cases: List[str]
    data: List[str]
    comparisons: List[str]


class SourceDistillationOutput(BaseModel):
    sources: List[DistilledSourceOutput]
    common_themes: List[str]
    contradictions: List[Dict[str, str]]
    material_by_type: MaterialByTypeOutput


class UniqueAngleOutput(BaseModel):
    angle: str
    reason: str


class WritingRecommendationsOutput(BaseModel):
    recommended_structure: str
    must_cover: List[str]
    can_skip: List[str]
    differentiation: str


class GapAnalysisOutput(BaseModel):
    content_gaps: List[str]
    unique_angles: List[UniqueAngleOutput]
    writing_recommendations: WritingRecommendationsOutput


class DeepResearchGapOutput(BaseModel):
    topic: str
    reason: str
    search_query: str


class DeepResearchAnalysisOutput(BaseModel):
    gaps: List[DeepResearchGapOutput]
    coverage_score: int = Field(ge=0, le=100)


class GoalExtractionOutput(BaseModel):
    rational: str
    evidence: str
    summary: str


class DetectedKnowledgeGapOutput(BaseModel):
    gap: str
    refined_query: str


class DetectedKnowledgeGapsOutput(RootModel[List[DetectedKnowledgeGapOutput]]):
    pass


class CredibilityScoreOutput(BaseModel):
    index: int = Field(ge=1)
    authority: float = Field(ge=0, le=10)
    freshness: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    depth: float = Field(ge=0, le=10)
    total_score: float = Field(ge=0, le=10)
    reason: str


class CredibilityScoresOutput(RootModel[List[CredibilityScoreOutput]]):
    @model_validator(mode="before")
    @classmethod
    def unwrap_results(cls, value):
        if isinstance(value, dict) and "results" in value:
            return value["results"]
        return value


class QueryListOutput(RootModel[List[str]]):
    @model_validator(mode="before")
    @classmethod
    def unwrap_queries(cls, value):
        if isinstance(value, dict) and "queries" in value:
            return value["queries"]
        return value


class SearchRouterOutput(BaseModel):
    sources: List[str]
    arxiv_query: str = ""
    blog_query: str = ""


class KnowledgeGapsOutput(BaseModel):
    gaps: List[KnowledgeGap]


__all__ = [
    "ArtistGenerationOutput",
    "AudienceAnalysis",
    "BlogOutline",
    "CodeBlock",
    "CodeGenerationOutput",
    "ContentEvaluationOutput",
    "CredibilityScoresOutput",
    "DeepResearchAnalysisOutput",
    "DepthCheckOutput",
    "DetectedKnowledgeGapsOutput",
    "FactCheckOutput",
    "GapAnalysisOutput",
    "GoalExtractionOutput",
    "HumanizerRewriteOutput",
    "HumanizerScoreOutput",
    "ImageResource",
    "InformationArchitecture",
    "InstructionalAnalysis",
    "KnowledgeGap",
    "KnowledgeGapsOutput",
    "LearningObjective",
    "QuestionResult",
    "QueryListOutput",
    "ResearchSummaryOutput",
    "ReviewIssue",
    "ReviewerOutput",
    "SearchHistoryItem",
    "SearchResult",
    "SearchRouterOutput",
    "SectionContent",
    "SectionOutline",
    "SourceDistillationOutput",
    "SummaryOutput",
    "ThreadCheckOutput",
    "VaguePoint",
    "VerbatimDataItem",
    "VoiceCheckOutput",
]
