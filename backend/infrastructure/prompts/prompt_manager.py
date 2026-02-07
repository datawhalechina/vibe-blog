"""
统一 Prompt 管理器 - 使用 Jinja2 模板管理所有 Prompt

基于 blog_generator 版本改造，支持多子目录模板加载。
模板引用使用子目录前缀：render("blog/planner", ...) 替代 render("planner", ...)
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# 默认模板根目录
BASE_DIR = os.path.dirname(__file__)


class PromptManager:
    """
    统一 Prompt 管理器 - 使用 Jinja2 模板渲染 Prompt

    支持从 infrastructure/prompts/ 下的子目录加载模板：
    - blog/          博客生成
    - reviewer/      内容评审
    - image_styles/  图片风格
    - shared/        共享模板
    """

    _instance: Optional['PromptManager'] = None

    def __init__(self, base_dir: str = None):
        """
        初始化 Prompt 管理器

        Args:
            base_dir: 模板根目录路径，默认为 infrastructure/prompts/
        """
        self.base_dir = base_dir or BASE_DIR

        # 初始化 Jinja2 环境，加载整个目录树
        self.env = Environment(
            loader=FileSystemLoader(self.base_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # 添加自定义过滤器
        self.env.filters['truncate'] = self._truncate
        self.env.filters['tojson'] = self._tojson

        logger.info(f"Prompt 管理器初始化完成，模板根目录: {self.base_dir}")

    @classmethod
    def get_instance(cls, base_dir: str = None) -> 'PromptManager':
        """
        获取单例实例

        Args:
            base_dir: 模板根目录路径

        Returns:
            PromptManager 实例
        """
        if cls._instance is None:
            cls._instance = cls(base_dir)
        return cls._instance

    def _truncate(self, text: str, length: int = 500, end: str = '...') -> str:
        """截断文本"""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length] + end

    def _tojson(self, obj: Any, indent: int = None) -> str:
        """转换为 JSON 字符串"""
        import json
        return json.dumps(obj, ensure_ascii=False, indent=indent)

    def render(self, template_name: str, **kwargs) -> str:
        """
        渲染模板

        Args:
            template_name: 模板名称，支持子目录前缀 (如 "blog/planner")，不含 .j2 后缀
            **kwargs: 模板变量

        Returns:
            渲染后的字符串
        """
        # 自动添加 .j2 后缀
        if not template_name.endswith('.j2'):
            template_name = f"{template_name}.j2"

        try:
            template = self.env.get_template(template_name)
            # 自动注入当前时间戳
            kwargs['current_time'] = datetime.now().strftime('%Y年%m月%d日')
            kwargs['current_year'] = datetime.now().year
            kwargs['current_month'] = datetime.now().month
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"模板渲染失败 [{template_name}]: {e}")
            raise

    # ========== Blog Agent 便捷方法 ==========

    def render_researcher(
        self,
        topic: str,
        search_depth: str = "medium",
        target_audience: str = "intermediate",
        search_results: list = None
    ) -> str:
        """渲染 Researcher Prompt"""
        return self.render(
            'blog/researcher',
            topic=topic,
            search_depth=search_depth,
            target_audience=target_audience,
            search_results=search_results or []
        )

    def render_search_query(
        self,
        topic: str,
        target_audience: str = "intermediate"
    ) -> str:
        """渲染搜索查询 Prompt"""
        return self.render(
            'blog/search_query',
            topic=topic,
            target_audience=target_audience
        )

    def render_planner(
        self,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        audience_adaptation: str = "technical-beginner",
        target_length: str = "medium",
        background_knowledge: str = None,
        key_concepts: list = None,
        target_sections_count: int = None,
        target_images_count: int = None,
        target_code_blocks_count: int = None,
        target_word_count: int = None,
        instructional_analysis: dict = None,
        verbatim_data: list = None
    ) -> str:
        """渲染 Planner Prompt"""
        return self.render(
            'blog/planner',
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            audience_adaptation=audience_adaptation,
            target_length=target_length,
            background_knowledge=background_knowledge,
            key_concepts=key_concepts or [],
            target_sections_count=target_sections_count,
            target_images_count=target_images_count,
            target_code_blocks_count=target_code_blocks_count,
            target_word_count=target_word_count,
            instructional_analysis=instructional_analysis,
            verbatim_data=verbatim_data or []
        )

    def render_writer(
        self,
        section_outline: dict,
        previous_section_summary: str = None,
        next_section_preview: str = None,
        background_knowledge: str = None,
        audience_adaptation: str = "technical-beginner",
        search_results: list = None,
        verbatim_data: list = None,
        learning_objectives: list = None
    ) -> str:
        """渲染 Writer Prompt"""
        return self.render(
            'blog/writer',
            section_outline=section_outline,
            previous_section_summary=previous_section_summary,
            next_section_preview=next_section_preview,
            background_knowledge=background_knowledge,
            audience_adaptation=audience_adaptation,
            search_results=search_results or [],
            verbatim_data=verbatim_data or [],
            learning_objectives=learning_objectives or []
        )

    def render_writer_enhance(
        self,
        original_content: str,
        vague_points: list
    ) -> str:
        """渲染 Writer 增强 Prompt"""
        return self.render(
            'blog/writer_enhance',
            original_content=original_content,
            vague_points=vague_points or []
        )

    def render_writer_correct(
        self,
        section_title: str,
        original_content: str,
        issues: list
    ) -> str:
        """渲染 Writer 更正 Prompt（Mini/Short 模式专用）"""
        return self.render(
            'blog/writer_correct',
            section_title=section_title,
            original_content=original_content,
            issues=issues or []
        )

    def render_coder(
        self,
        code_description: str,
        context: str,
        language: str = "python",
        complexity: str = "medium"
    ) -> str:
        """渲染 Coder Prompt"""
        return self.render(
            'blog/coder',
            code_description=code_description,
            context=context,
            language=language,
            complexity=complexity
        )

    def render_artist(
        self,
        image_type: str,
        description: str,
        context: str,
        audience_adaptation: str = "technical-beginner",
        article_title: str = "",
        illustration_type: str = ""
    ) -> str:
        """渲染 Artist Prompt"""
        return self.render(
            'blog/artist',
            image_type=image_type,
            description=description,
            context=context,
            audience_adaptation=audience_adaptation,
            article_title=article_title,
            illustration_type=illustration_type
        )

    def render_questioner(
        self,
        section_content: str,
        section_outline: dict,
        depth_requirement: str = "medium"
    ) -> str:
        """渲染 Questioner Prompt"""
        return self.render(
            'blog/questioner',
            section_content=section_content,
            section_outline=section_outline,
            depth_requirement=depth_requirement
        )

    def render_reviewer(
        self,
        document: str,
        outline: dict,
        verbatim_data: list = None,
        learning_objectives: list = None,
        search_results: list = None,
        background_knowledge: str = None
    ) -> str:
        """渲染 Reviewer Prompt"""
        return self.render(
            'blog/reviewer',
            document=document,
            outline=outline,
            search_results=search_results or [],
            verbatim_data=verbatim_data or [],
            learning_objectives=learning_objectives or [],
            background_knowledge=background_knowledge or ""
        )

    def render_assembler_header(
        self,
        title: str,
        subtitle: str,
        reading_time: int,
        core_value: str,
        table_of_contents: list,
        introduction: str,
        sections: list = None
    ) -> str:
        """渲染文章头部"""
        return self.render(
            'blog/assembler_header',
            title=title,
            subtitle=subtitle,
            reading_time=reading_time,
            core_value=core_value,
            table_of_contents=table_of_contents or [],
            introduction=introduction,
            sections=sections or []
        )

    def render_assembler_footer(
        self,
        summary_points: list,
        next_steps: str,
        reference_links: list,
        document_references: list = None
    ) -> str:
        """渲染文章尾部"""
        return self.render(
            'blog/assembler_footer',
            summary_points=summary_points or [],
            next_steps=next_steps or '',
            reference_links=reference_links or [],
            document_references=document_references or []
        )

    def render_knowledge_gap_detector(
        self,
        content: str,
        existing_knowledge: str,
        context: str = "",
        topic: str = ""
    ) -> str:
        """渲染知识空白检测 Prompt"""
        return self.render(
            'blog/knowledge_gap_detector',
            content=content,
            existing_knowledge=existing_knowledge,
            context=context,
            topic=topic
        )

    def render_writer_enhance_with_knowledge(
        self,
        original_content: str,
        new_knowledge: str,
        knowledge_gaps: list
    ) -> str:
        """渲染基于新知识增强内容的 Prompt"""
        return self.render(
            'blog/writer_enhance_knowledge',
            original_content=original_content,
            new_knowledge=new_knowledge,
            knowledge_gaps=knowledge_gaps or []
        )

    def render_cover_image_prompt(self, article_summary: str) -> str:
        """渲染封面图生成 Prompt"""
        return self.render(
            'blog/cover_image_prompt',
            article_summary=article_summary
        )

    def render_cover_video_prompt(self) -> str:
        """渲染封面视频动画 Prompt"""
        return self.render('blog/cover_video_prompt')

    def render_search_summarizer(
        self,
        gaps: list,
        results: list
    ) -> str:
        """渲染搜索结果摘要 Prompt"""
        return self.render(
            'blog/search_summarizer',
            gaps=gaps or [],
            results=results or []
        )

    def render_search_router(self, topic: str) -> str:
        """渲染搜索源路由 Prompt"""
        return self.render('blog/search_router', topic=topic)

    def render_article_summary(self, title: str, content: str, max_length: int = None) -> str:
        """渲染文章摘要提炼 Prompt"""
        return self.render('blog/article_summary', title=title, content=content, max_length=max_length)

    def render_artist_default(self, prompt: str, caption: str) -> str:
        """渲染默认图片生成 Prompt（卡通手绘风格）"""
        return self.render('blog/artist_default', prompt=prompt, caption=caption)

    def render_section_summary_image(
        self,
        section_title: str,
        section_summary: str,
        key_concepts: list = None
    ) -> str:
        """渲染章节总结配图 Prompt"""
        return self.render(
            'blog/section_summary_image',
            section_title=section_title,
            section_summary=section_summary,
            key_concepts=key_concepts or []
        )

    def render_book_scanner(
        self,
        existing_books_info: str,
        new_blogs_info: str
    ) -> str:
        """渲染书籍扫描决策 Prompt"""
        return self.render(
            'blog/book_scanner',
            existing_books_info=existing_books_info,
            new_blogs_info=new_blogs_info
        )

    def render_book_introduction(
        self,
        book_title: str,
        book_theme: str,
        chapters_count: int,
        chapters: list
    ) -> str:
        """渲染书籍简介生成 Prompt"""
        return self.render(
            'blog/book_introduction',
            book_title=book_title,
            book_theme=book_theme,
            chapters_count=chapters_count,
            chapters=chapters
        )

    def render_book_classifier(
        self,
        existing_books_info: str,
        blogs_info: str,
        reference_books_info: str = ""
    ) -> str:
        """渲染博客分类 Prompt（第一步：只做分类）"""
        return self.render(
            'blog/book_classifier',
            existing_books_info=existing_books_info,
            blogs_info=blogs_info,
            reference_books_info=reference_books_info
        )

    def render_book_outline_generator(
        self,
        book_title: str,
        book_theme: str,
        book_description: str,
        blogs_info: str
    ) -> str:
        """渲染书籍大纲生成 Prompt（第二步：生成大纲）"""
        return self.render(
            'blog/book_outline_generator',
            book_title=book_title,
            book_theme=book_theme,
            book_description=book_description,
            blogs_info=blogs_info
        )

    def render_outline_expander(
        self,
        book: dict,
        existing_chapters: list,
        search_results: list = None
    ) -> str:
        """渲染大纲扩展 Prompt"""
        return self.render(
            'blog/outline_expander',
            book=book,
            existing_chapters=existing_chapters or [],
            search_results=search_results or []
        )

    def render_homepage_generator(
        self,
        book: dict,
        outline: dict
    ) -> str:
        """渲染首页生成 Prompt"""
        return self.render(
            'blog/homepage_generator',
            book=book,
            outline=outline or {}
        )

    def render_missing_diagram_detector(
        self,
        section_title: str,
        content: str
    ) -> str:
        """渲染缺失图表检测的 Prompt"""
        return self.render(
            'blog/missing_diagram_detector',
            section_title=section_title,
            content=content
        )

    # ========== 小红书相关 Prompt ==========

    def render_xhs_outline(
        self,
        topic: str,
        count: int = 4,
        content: str = None
    ) -> str:
        """渲染小红书大纲生成 Prompt"""
        return self.render(
            'blog/xhs_outline',
            topic=topic,
            count=count,
            content=content
        )

    def render_xhs_visual_prompts_batch(
        self,
        full_outline: str,
        page_count: int,
        user_topic: str = None
    ) -> str:
        """渲染小红书视觉指令（批量版本）"""
        return self.render(
            'blog/xhs_visual_prompt_ghibli_dynamic',
            full_outline=full_outline,
            page_count=page_count,
            user_topic=user_topic
        )

    def render_xhs_image(
        self,
        page_content: str,
        page_type: str = "content",
        style: str = "hand_drawn",
        reference_image: bool = False,
        user_topic: str = None,
        full_outline: str = None,
        page_index: int = 0,
        layout: str = None,
        shape: str = None
    ) -> str:
        """渲染小红书图片生成 Prompt（单页版本）"""
        return self.render(
            'blog/xhs_image',
            page_content=page_content,
            page_type=page_type,
            style=style,
            reference_image=reference_image,
            user_topic=user_topic,
            full_outline=full_outline
        )

    def render_xhs_content(
        self,
        topic: str,
        outline: str
    ) -> str:
        """渲染小红书文案生成 Prompt"""
        return self.render(
            'blog/xhs_content',
            topic=topic,
            outline=outline
        )


# 全局实例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取 Prompt 管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager

