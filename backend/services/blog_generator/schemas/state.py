"""
共享状态和数据模型定义
"""

import os
from typing import TypedDict, List, Optional, Literal
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
    content: str  # Markdown 内容
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
    content: str  # Mermaid 代码 或 AI Prompt 或 Python 代码
    rendered_path: Optional[str] = None  # 渲染后的图片路径
    caption: str


class VaguePoint(BaseModel):
    """模糊点 (Questioner 输出)"""
    location: str  # 段落位置或引用文本
    issue: str  # 问题描述
    question: str  # 追问问题
    suggestion: str  # 建议补充的内容类型


class QuestionResult(BaseModel):
    """追问结果"""
    section_id: str
    is_detailed_enough: bool
    vague_points: List[VaguePoint] = Field(default_factory=list)
    depth_score: int  # 0-100


class ReviewIssue(BaseModel):
    """审核问题"""
    section_id: str
    issue_type: Literal["logic", "accuracy", "completeness", "image", "readability"]
    severity: Literal["high", "medium", "low"]
    description: str
    suggestion: str


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
    round: int  # 第几轮搜索
    queries: List[str]  # 本轮搜索的查询
    results_count: int  # 结果数量
    gaps_addressed: List[str]  # 本轮解决的知识空白


class SharedState(TypedDict):
    """Multi-Agent 共享状态"""
    
    # 输入
    topic: str
    article_type: Literal["problem-solution", "tutorial", "comparison"]
    target_audience: Literal["beginner", "intermediate", "advanced"]
    audience_adaptation: str  # 受众适配类型: default/high-school/children/professional
    target_length: Literal["mini", "short", "medium", "long", "custom"]
    source_material: Optional[str]
    image_style: str  # 图片风格 ID
    
    # 文档知识 (用户上传的文档)
    document_ids: List[str]  # 用户上传的文档 ID 列表
    document_knowledge: List[dict]  # 文档解析后的知识条目
    
    # 素材收集 (Researcher 输出)
    search_results: List[dict]  # 搜索结果列表
    background_knowledge: Optional[str]  # 背景知识摘要
    key_concepts: List[str]  # 提取的核心概念
    reference_links: List[str]  # 参考链接 (网络来源)
    document_references: List[dict]  # 文档来源引用
    knowledge_source_stats: dict  # 知识来源统计
    
    # 多轮搜索相关
    search_count: int  # 当前搜索次数
    max_search_count: int  # 最大搜索次数
    search_history: List[dict]  # 搜索历史记录
    knowledge_gaps: List[dict]  # 检测到的知识空白
    accumulated_knowledge: str  # 累积的背景知识
    
    # 大纲 (Planner 输出)
    outline: Optional[dict]
    
    # 章节内容 (Writer 输出)
    sections: List[dict]
    
    # 代码块 (Coder 输出)
    code_blocks: List[dict]
    
    # 图片资源 (Artist 输出)
    images: List[dict]
    
    # 追问结果 (Questioner 输出)
    question_results: List[dict]
    all_sections_detailed: bool
    questioning_count: int  # 追问次数，防止无限循环
    
    # 审核结果 (Reviewer 输出)
    review_score: int
    review_issues: List[dict]
    review_approved: bool
    revision_count: int  # 修订次数，防止无限循环
    
    # 最终输出 (Assembler 输出)
    final_markdown: Optional[str]
    final_html: Optional[str]
    output_folder: Optional[str]
    
    # 文章长度配置
    custom_config: Optional[dict]  # 自定义配置
    target_sections_count: Optional[int]  # 目标章节数
    target_images_count: Optional[int]  # 目标配图数
    target_code_blocks_count: Optional[int]  # 目标代码块数
    target_word_count: Optional[int]  # 目标字数
    
    # 错误信息
    error: Optional[str]


def get_max_search_count(target_length: str) -> int:
    """
    根据文章长度获取最大搜索次数
    
    可通过环境变量配置：
    - MULTI_SEARCH_MAX_MINI: Mini 模式最大搜索次数，默认 1
    - MULTI_SEARCH_MAX_SHORT: 短文最大搜索次数，默认 3
    - MULTI_SEARCH_MAX_MEDIUM: 中等文章最大搜索次数，默认 5
    - MULTI_SEARCH_MAX_LONG: 长文最大搜索次数，默认 8
    - MULTI_SEARCH_MAX_CUSTOM: 自定义模式最大搜索次数，默认 5
    """
    max_search_map = {
        'mini': int(os.getenv('MULTI_SEARCH_MAX_MINI', '1')),
        'short': int(os.getenv('MULTI_SEARCH_MAX_SHORT', '3')),
        'medium': int(os.getenv('MULTI_SEARCH_MAX_MEDIUM', '5')),
        'long': int(os.getenv('MULTI_SEARCH_MAX_LONG', '8')),
        'custom': int(os.getenv('MULTI_SEARCH_MAX_CUSTOM', '5'))
    }
    return max_search_map.get(target_length, max_search_map['medium'])


def create_initial_state(
    topic: str,
    article_type: str = "tutorial",
    target_audience: str = "intermediate",
    audience_adaptation: str = "default",
    target_length: str = "medium",
    source_material: str = None,
    document_ids: List[str] = None,
    document_knowledge: List[dict] = None,
    image_style: str = "",
    # 新增：文章长度配置参数
    custom_config: dict = None,
    target_sections_count: int = None,
    target_images_count: int = None,
    target_code_blocks_count: int = None,
    target_word_count: int = None,
) -> SharedState:
    """创建初始状态"""
    return SharedState(
        topic=topic,
        article_type=article_type,
        target_audience=target_audience,
        audience_adaptation=audience_adaptation,
        target_length=target_length,
        source_material=source_material,
        image_style=image_style,
        # 文档知识
        document_ids=document_ids or [],
        document_knowledge=document_knowledge or [],
        # 素材收集
        search_results=[],
        background_knowledge=None,
        key_concepts=[],
        reference_links=[],
        document_references=[],
        knowledge_source_stats={},
        # 多轮搜索相关
        search_count=0,
        max_search_count=get_max_search_count(target_length),
        search_history=[],
        knowledge_gaps=[],
        accumulated_knowledge="",
        # 其他字段
        outline=None,
        sections=[],
        code_blocks=[],
        images=[],
        question_results=[],
        all_sections_detailed=False,
        questioning_count=0,
        review_score=0,
        review_issues=[],
        review_approved=False,
        revision_count=0,
        final_markdown=None,
        final_html=None,
        output_folder=None,
        error=None,
        # 新增：文章长度配置
        custom_config=custom_config,
        target_sections_count=target_sections_count,
        target_images_count=target_images_count,
        target_code_blocks_count=target_code_blocks_count,
        target_word_count=target_word_count,
    )
