"""
小红书内容生成服务

复用现有服务：
- PromptManager: 模板渲染
- NanoBananaService: 图片生成
- VideoService: 动画生成
- OSSService: 文件上传
- LLMService: 文本生成
"""

import re
import json
import logging
import asyncio
import threading
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class XHSPage:
    """小红书页面"""
    index: int
    page_type: str  # cover, content, summary
    content: str


@dataclass
class XHSGenerateResult:
    """小红书生成结果"""
    topic: str
    style: str
    pages: List[XHSPage] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    video_url: Optional[str] = None
    titles: List[str] = field(default_factory=list)
    copywriting: str = ""
    tags: List[str] = field(default_factory=list)
    outline: str = ""
    article: str = ""  # 2000字科普短文


class XHSService:
    """小红书内容生成服务"""
    
    def __init__(
        self,
        llm_client,
        image_service=None,
        video_service=None,
        oss_service=None
    ):
        """
        初始化小红书服务
        
        Args:
            llm_client: LLM 客户端
            image_service: 图片生成服务（NanoBananaService）
            video_service: 视频生成服务
            oss_service: OSS 服务
        """
        self.llm = llm_client
        self.image_service = image_service
        self.video_service = video_service
        self.oss_service = oss_service
        
        # 导入 PromptManager
        from services.blog_generator.prompts import get_prompt_manager
        self.prompt_manager = get_prompt_manager()
        
        # 导入智能搜索服务
        try:
            from services.blog_generator.services.smart_search_service import get_smart_search_service
            self.smart_search = get_smart_search_service()
        except Exception as e:
            logger.warning(f"智能搜索服务初始化失败: {e}")
            self.smart_search = None
        
        logger.info("XHSService 初始化完成")
    
    async def generate_series(
        self,
        topic: str,
        count: int = 4,
        style: str = "hand_drawn",
        content: str = None,
        generate_video: bool = True,
        layouts: List[str] = None
    ) -> XHSGenerateResult:
        """
        生成完整的小红书系列
        
        Args:
            topic: 主题
            count: 页面数量（包括封面）
            style: 风格（hand_drawn/claymation/ghibli_summer）
            content: 参考内容（可选）
            generate_video: 是否生成动画封面
            layouts: 可选，为每页指定布局，如 ['单页大图', '标准网格', '标准网格', '单页大图']
                     如果不指定，则自动选择
            
        Returns:
            XHSGenerateResult
        """
        logger.info(f"开始生成小红书系列: topic={topic}, count={count}, style={style}, layouts={layouts}")
        
        result = XHSGenerateResult(topic=topic, style=style)
        
        # Step 1: 生成大纲
        logger.info("Step 1: 生成大纲...")
        outline, pages, article_text = await self._generate_outline(topic, count, content)
        result.outline = outline
        result.pages = pages
        result.article = article_text  # 保存短文内容
        logger.info(f"大纲生成完成，共 {len(pages)} 页")
        if article_text:
            logger.info(f"📝 生成了 {len(article_text)} 字的科普短文")
        
        # Step 2: 生成所有页的视觉指令（一次 LLM 调用）
        logger.info("Step 2: 生成所有页的视觉指令...")
        
        visual_prompts = []
        if style == 'ghibli_summer':
            # 一次性生成所有页的视觉 Prompt（传入短文作为参考）
            visual_prompts = await self._generate_all_visual_prompts(outline, len(pages), topic, article_text)
            logger.info(f"视觉指令生成完成，共 {len(visual_prompts)} 页")
        
        # Step 3: 并行生成所有图片 + 文案
        logger.info("Step 3: 并行生成所有图片和文案...")
        
        # 创建所有图片生成任务
        image_tasks = []
        for i, page in enumerate(pages):
            # 使用预生成的视觉 Prompt（如果有）
            visual_prompt = visual_prompts[i] if i < len(visual_prompts) else None
            image_tasks.append(self._generate_single_image_v2(
                page, style, topic, outline, visual_prompt=visual_prompt
            ))
        
        # 文案生成任务
        content_task = self._generate_content(topic, outline)
        
        # 并行执行所有图片生成 + 文案生成
        all_results = await asyncio.gather(*image_tasks, content_task)
        
        # 分离结果：前 N 个是图片，最后一个是文案
        image_urls = [url for url in all_results[:-1] if url]
        content_result = all_results[-1]
        
        logger.info(f"并行生成完成: {len(image_urls)} 张图片")
        
        # Step 3: 生成动画封面（需要封面图完成后）
        video_url = None
        if generate_video and image_urls:
            logger.info("Step 3: 生成动画封面...")
            video_url = await self._generate_video(image_urls[0])
        
        result.image_urls = image_urls
        result.video_url = video_url
        result.titles = content_result.get('titles', [])
        result.copywriting = content_result.get('copywriting', '')
        result.tags = content_result.get('tags', [])
        
        logger.info(f"小红书系列生成完成: {len(result.image_urls)} 张图片, 视频={result.video_url is not None}")
        return result
    
    async def _generate_outline(
        self,
        topic: str,
        count: int,
        content: str = None
    ) -> tuple:
        """
        生成大纲（带搜索增强）
        
        流程：
        1. 搜索相关知识（复用智能搜索服务）
        2. 整合搜索结果为背景知识
        3. 基于背景知识生成大纲
        
        Returns:
            (outline_text, pages_list)
        """
        # Step 1: 搜索相关知识
        search_content = content or ""
        
        try:
            from services.blog_generator.services.smart_search_service import get_smart_search_service
            from services.blog_generator.services.search_service import get_search_service
            
            smart_service = get_smart_search_service()
            search_service = get_search_service()
            
            if smart_service:
                # 使用智能搜索（LLM 路由 + 多源并行）
                logger.info(f"🧠 [大纲生成] 启动智能知识源搜索: {topic}")
                loop = asyncio.get_event_loop()
                search_result = await loop.run_in_executor(
                    None,
                    lambda: smart_service.search(topic=topic, article_type='科普', max_results_per_source=5)
                )
                
                if search_result.get('success') and search_result.get('results'):
                    # 整合搜索结果为背景知识
                    search_knowledge = self._format_search_results(search_result['results'])
                    search_content = f"{content or ''}\n\n## 搜索到的相关知识\n\n{search_knowledge}"
                    logger.info(f"🧠 [大纲生成] 智能搜索完成，获取 {len(search_result['results'])} 条结果")
                    
            elif search_service and search_service.is_available():
                # 使用普通搜索
                logger.info(f"🌐 [大纲生成] 启动网络搜索: {topic}")
                loop = asyncio.get_event_loop()
                search_result = await loop.run_in_executor(
                    None,
                    lambda: search_service.search(f"{topic} 教程 知识点", max_results=10)
                )
                
                if search_result.get('success') and search_result.get('results'):
                    search_knowledge = self._format_search_results(search_result['results'])
                    search_content = f"{content or ''}\n\n## 搜索到的相关知识\n\n{search_knowledge}"
                    logger.info(f"🌐 [大纲生成] 网络搜索完成，获取 {len(search_result['results'])} 条结果")
            else:
                logger.info("📋 [大纲生成] 搜索服务不可用，使用原始内容生成大纲")
                
        except Exception as e:
            logger.warning(f"⚠️ [大纲生成] 搜索失败，使用原始内容: {e}")
        
        # Step 2: 生成大纲
        prompt = self.prompt_manager.render_xhs_outline(
            topic=topic,
            count=count,
            content=search_content
        )
        
        # 在线程池中执行同步 LLM 调用
        loop = asyncio.get_event_loop()
        outline_text = await loop.run_in_executor(
            None,
            lambda: self._call_llm_sync(prompt)
        )
        
        # 解析大纲（新格式返回 pages 和 article）
        pages, article_text = self._parse_outline(outline_text)
        
        # 如果有短文，记录日志
        if article_text:
            logger.info(f"📝 [大纲生成] 生成了 {len(article_text)} 字的科普短文")
        
        return outline_text, pages, article_text
    
    def _format_search_results(self, results: List[Dict]) -> str:
        """
        将搜索结果格式化为背景知识文本
        
        Args:
            results: 搜索结果列表
            
        Returns:
            格式化的背景知识文本
        """
        formatted_parts = []
        
        for i, item in enumerate(results[:10], 1):
            title = item.get('title', '').strip()
            content = item.get('content', '').strip()
            source = item.get('source', '').strip()
            
            if title or content:
                part = f"### {i}. {title or '未知标题'}"
                if source:
                    part += f" ({source})"
                part += f"\n{content[:1000]}"
                formatted_parts.append(part)
        
        return "\n\n".join(formatted_parts)
    
    def _parse_outline(self, outline_text: str) -> tuple:
        """
        解析大纲文本为页面列表
        
        新格式支持：
        - <article>...</article> 包含 2000 字短文
        - <outline>...</outline> 包含页面大纲
        
        Returns:
            (pages_list, article_text) - 页面列表和短文内容
        """
        article_text = ""
        outline_content = outline_text
        
        # 提取短文内容（如果有）
        article_match = re.search(r'<article>(.*?)</article>', outline_text, re.DOTALL | re.IGNORECASE)
        if article_match:
            article_text = article_match.group(1).strip()
            logger.info(f"📝 [大纲解析] 提取到短文，长度: {len(article_text)} 字")
        
        # 提取大纲内容（如果有）
        outline_match = re.search(r'<outline>(.*?)</outline>', outline_text, re.DOTALL | re.IGNORECASE)
        if outline_match:
            outline_content = outline_match.group(1).strip()
            logger.info(f"📋 [大纲解析] 提取到大纲内容")
        
        # 按 <page> 分割页面
        if '<page>' in outline_content.lower():
            pages_raw = re.split(r'<page>', outline_content, flags=re.IGNORECASE)
        else:
            # 向后兼容：如果没有 <page> 则使用 ---
            pages_raw = outline_content.split("---")
        
        pages = []
        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue
            
            # 解析页面类型
            page_type = "content"
            type_match = re.match(r"\[(\S+)\]", page_text)
            if type_match:
                type_cn = type_match.group(1)
                type_mapping = {
                    "封面": "cover",
                    "内容": "content",
                    "总结": "summary",
                }
                page_type = type_mapping.get(type_cn, "content")
            
            pages.append(XHSPage(
                index=len(pages),
                page_type=page_type,
                content=page_text
            ))
        
        return pages, article_text
    
    async def _generate_all_visual_prompts(
        self,
        outline: str,
        page_count: int,
        topic: str,
        article: str = ""
    ) -> List[str]:
        """
        一次性生成所有页的视觉指令（ghibli_summer 风格专用）
        
        Args:
            outline: 完整大纲
            page_count: 页面数量
            topic: 主题
            article: 2000字科普短文（可选，用于丰富分镜内容）
            
        Returns:
            每页的视觉 Prompt 列表
        """
        # 如果有短文，将其与大纲合并作为输入
        full_content = outline
        if article:
            full_content = f"## 科普短文（作为分镜参考）\n\n{article}\n\n---\n\n## 大纲\n\n{outline}"
            logger.info(f"📝 [分镜生成] 使用短文作为参考，长度: {len(article)} 字")
        
        # 渲染批量视觉指令模板
        meta_prompt = self.prompt_manager.render_xhs_visual_prompts_batch(
            full_outline=full_content,
            page_count=page_count,
            user_topic=topic
        )
        
        # 调用 LLM 生成所有页的视觉指令
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._call_llm_sync(meta_prompt)
        )
        
        # 解析响应，提取每页的视觉 Prompt
        visual_prompts = self._parse_visual_prompts(response, page_count)
        
        return visual_prompts
    
    def _parse_visual_prompts(self, response: str, expected_count: int) -> List[str]:
        """
        解析 LLM 响应，提取每页的视觉 Prompt
        
        Args:
            response: LLM 响应文本
            expected_count: 期望的页面数量
            
        Returns:
            每页的视觉 Prompt 列表
        """
        visual_prompts = []
        
        # 按 <page_N> 标签分割
        for i in range(1, expected_count + 1):
            # 匹配 <page_N>...</page_N> 或 <page_N>...<page_N+1>
            pattern = rf'<page_{i}>(.*?)(?=<page_{i+1}>|</page_{i}>|<page_\d+>|\Z)'
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            
            if match:
                content = match.group(1).strip()
                # 移除结束标签（如果有）
                content = re.sub(rf'</page_{i}>', '', content, flags=re.IGNORECASE).strip()
                visual_prompts.append(content)
            else:
                # 如果没找到，尝试其他格式
                logger.warning(f"未找到 page_{i} 的视觉指令，使用空字符串")
                visual_prompts.append("")
        
        logger.info(f"解析视觉指令完成: {len(visual_prompts)} 页，非空 {sum(1 for p in visual_prompts if p)} 页")
        return visual_prompts
    
    async def _generate_single_image_v2(
        self,
        page: XHSPage,
        style: str,
        topic: str,
        outline: str,
        visual_prompt: str = None
    ) -> Optional[str]:
        """
        生成单张图片（V2 版本，支持预生成的视觉 Prompt）
        
        Args:
            page: 页面对象
            style: 风格
            topic: 主题
            outline: 大纲
            visual_prompt: 预生成的视觉 Prompt（ghibli_summer 风格）
        """
        if not self.image_service or not page:
            return None
        
        from services.image_service import AspectRatio
        
        logger.info(f"生成图片: {page.page_type} (index={page.index})")
        
        # 确定最终的图片生成 Prompt
        if style == 'ghibli_summer' and visual_prompt:
            # 使用预生成的视觉 Prompt
            prompt = visual_prompt
            logger.info(f"[批量模式] 使用预生成的视觉 Prompt 生成图片...")
        else:
            # 其他风格，直接使用模板渲染的 Prompt
            prompt = self.prompt_manager.render_xhs_image(
                page_content=page.content,
                page_type=page.page_type,
                style=style,
                reference_image=False,
                user_topic=topic,
                full_outline=outline
            )
        
        # 在线程池中执行同步图片生成
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.image_service.generate(
                prompt=prompt,
                aspect_ratio=AspectRatio.PORTRAIT_3_4,
                download=True
            )
        )
        
        if result and result.oss_url:
            return result.oss_url
        elif result and result.url:
            return result.url
        return None
    
    async def _generate_single_image(
        self,
        page: XHSPage,
        style: str,
        topic: str,
        outline: str,
        is_first: bool = False,
        layout: str = None,
        shape: str = None
    ) -> Optional[str]:
        """
        生成单张图片（真正并行化版本）
        
        Args:
            page: 页面对象
            style: 风格
            topic: 主题
            outline: 大纲
            is_first: 是否是第一张图
            layout: 布局类型（单页大图/电影感/标准网格/密集网格/条漫）
            shape: 格子形状（矩形/斜切/圆形/无边框/出血）
        """
        if not self.image_service or not page:
            return None
        
        from services.image_service import AspectRatio
        
        logger.info(f"生成图片: {page.page_type} (index={page.index}, layout={layout}, shape={shape})")
        
        # 第一步：生成 LLM Prompt（用于 ghibli_summer 两步法）
        llm_prompt = self.prompt_manager.render_xhs_image(
            page_content=page.content,
            page_type=page.page_type,
            style=style,
            reference_image=not is_first,
            user_topic=topic,
            full_outline=outline,
            page_index=page.index,
            layout=layout,
            shape=shape
        )
        
        # 两步法：ghibli_summer 风格需要先用 LLM 生成视觉 Prompt
        if style == 'ghibli_summer':
            logger.info(f"[两步法] Step 1: LLM 生成视觉 Prompt (layout={layout}, shape={shape})...")
            # 在线程池中执行同步 LLM 调用，实现真正并行
            loop = asyncio.get_event_loop()
            visual_prompt = await loop.run_in_executor(
                None,
                lambda: self._call_llm_sync(llm_prompt)
            )
            logger.info(f"[两步法] Step 2: 使用视觉 Prompt 生成图片...")
            prompt = visual_prompt
        else:
            prompt = llm_prompt
        
        # 在线程池中执行同步图片生成，实现真正并行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.image_service.generate(
                prompt=prompt,
                aspect_ratio=AspectRatio.PORTRAIT_3_4,
                download=True
            )
        )
        
        if result and result.oss_url:
            return result.oss_url
        elif result and result.url:
            return result.url
        return None
    
    async def _generate_video(self, cover_image_url: str) -> Optional[str]:
        """生成动画封面"""
        if not self.video_service:
            logger.warning("视频服务未配置，跳过动画生成")
            return None
        
        try:
            # 使用现有的封面视频生成 Prompt
            video_prompt = self.prompt_manager.render_cover_video_prompt()
            
            # 调用视频服务（同步方法，在线程中执行）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.video_service.generate_from_image(
                    image_url=cover_image_url,
                    prompt=video_prompt
                )
            )
            
            video_url = result.oss_url if result and result.oss_url else (result.url if result else None)
            
            return video_url
        except Exception as e:
            logger.error(f"动画生成失败: {e}")
            return None
    
    async def _generate_content(self, topic: str, outline: str) -> Dict[str, Any]:
        """生成小红书文案（并行化版本）"""
        prompt = self.prompt_manager.render_xhs_content(
            topic=topic,
            outline=outline
        )
        
        # 在线程池中执行同步 LLM 调用，实现真正并行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._call_llm_sync(prompt)
        )
        
        # 解析 JSON 响应
        try:
            # 提取 JSON 部分
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"解析文案 JSON 失败: {e}")
            return {
                'titles': [topic],
                'copywriting': response,
                'tags': []
            }
    
    def _call_llm_sync(self, prompt: str, json_format: bool = False) -> str:
        """
        同步调用 LLM（统一使用 LLMService 标准接口）
        
        Args:
            prompt: 提示词
            json_format: 是否要求 JSON 格式响应
        """
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} if json_format else None
        )
        
        if response is None:
            raise Exception("LLM 返回空响应")
        
        return response
    
    # ========== SSE 实时推送支持 ==========
    
    def generate_async(
        self,
        task_id: str,
        topic: str,
        count: int = 4,
        style: str = "hand_drawn",
        content: str = None,
        generate_video: bool = True,
        layouts: List[str] = None,
        task_manager=None,
        app=None
    ):
        """
        异步生成小红书系列（在后台线程执行，通过 SSE 推送进度）
        
        Args:
            task_id: 任务 ID
            topic: 主题
            count: 页面数量
            style: 风格
            content: 参考内容
            generate_video: 是否生成动画封面
            layouts: 布局列表
            task_manager: 任务管理器（用于 SSE 推送）
            app: Flask 应用实例
        """
        def run_in_thread():
            try:
                if app:
                    with app.app_context():
                        asyncio.run(self._run_generation_with_sse(
                            task_id=task_id,
                            topic=topic,
                            count=count,
                            style=style,
                            content=content,
                            generate_video=generate_video,
                            layouts=layouts,
                            task_manager=task_manager
                        ))
                else:
                    asyncio.run(self._run_generation_with_sse(
                        task_id=task_id,
                        topic=topic,
                        count=count,
                        style=style,
                        content=content,
                        generate_video=generate_video,
                        layouts=layouts,
                        task_manager=task_manager
                    ))
            except Exception as e:
                logger.error(f"小红书生成失败: {e}", exc_info=True)
                if task_manager:
                    task_manager.send_event(task_id, 'error', {
                        'message': str(e),
                        'recoverable': False
                    })
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        logger.info(f"小红书生成任务已启动: {task_id}")
    
    async def _run_generation_with_sse(
        self,
        task_id: str,
        topic: str,
        count: int,
        style: str,
        content: str,
        generate_video: bool,
        layouts: List[str],
        task_manager
    ):
        """
        带 SSE 推送的生成流程
        
        流程顺序: 搜索 → 大纲 → 文案 → 分镜 → 图片 → 视频
        
        事件类型:
        - progress: 进度更新 {stage, progress, message, sub_progress?, detail?}
        - search: 搜索完成 {results_count, sources}
        - outline: 大纲生成完成 {outline, pages}
        - content: 文案生成完成 {titles, copywriting, tags}
        - storyboard: 分镜设计完成 {prompts}
        - image: 单张图片生成完成 {index, url, page_type, progress?}
        - image_progress: 图片生成进度 {index, progress, status}
        - video: 动画封面生成完成 {url}
        - complete: 全部完成
        - error: 发生错误
        - cancelled: 任务取消
        """
        def send_event(event_type: str, data: dict):
            """发送 SSE 事件"""
            if task_manager:
                task_manager.send_event(task_id, event_type, data)
        
        try:
            result = XHSGenerateResult(topic=topic, style=style)
            
            # 检查任务是否被取消
            def is_cancelled():
                return task_manager and task_manager.is_cancelled(task_id)
            
            # ========== Step 1: 智能搜索 ==========
            send_event('progress', {
                'stage': 'search',
                'progress': 5,
                'message': '正在搜索相关资料...',
                'detail': f'主题: {topic}'
            })
            
            if is_cancelled():
                send_event('cancelled', {'message': '任务已被用户取消'})
                return
            
            # 执行搜索
            search_results = []
            search_sources = []
            if self.smart_search:
                try:
                    raw_response = await asyncio.to_thread(
                        self.smart_search.search, topic
                    )
                    # smart_search.search() 返回 {'success': True, 'results': [...], 'sources_used': [...]}
                    if isinstance(raw_response, dict):
                        search_results = raw_response.get('results', [])
                        search_sources = raw_response.get('sources_used', [])
                    elif isinstance(raw_response, list):
                        search_results = raw_response
                    logger.info(f"🔍 [SSE] 搜索完成，获取 {len(search_results)} 条结果")
                except Exception as e:
                    logger.warning(f"搜索失败: {e}")
                    search_results = []
            
            # 安全获取预览
            preview_list = []
            for r in search_results[:5]:
                if isinstance(r, dict):
                    preview_list.append(r.get('title', '')[:50])
                else:
                    preview_list.append(str(r)[:50])
            
            send_event('search', {
                'results_count': len(search_results),
                'sources': search_sources,
                'preview': preview_list
            })
            
            send_event('progress', {
                'stage': 'search',
                'progress': 10,
                'message': f'搜索完成，获取 {len(search_results)} 条参考资料'
            })
            
            # ========== Step 2: 生成大纲 ==========
            send_event('progress', {
                'stage': 'outline',
                'progress': 12,
                'message': '正在生成内容大纲...'
            })
            
            if is_cancelled():
                send_event('cancelled', {'message': '任务已被用户取消'})
                return
            
            # 将搜索结果整合到 content 中
            search_context = ""
            if search_results:
                context_items = []
                for r in search_results[:8]:
                    if isinstance(r, dict):
                        title = r.get('title', '')
                        content_text = r.get('content', '')[:200]
                        context_items.append(f"- {title}: {content_text}")
                    else:
                        context_items.append(f"- {str(r)[:200]}")
                search_context = "\n\n【参考资料】\n" + "\n".join(context_items)
            
            full_content = (content or "") + search_context
            outline, pages, article_text = await self._generate_outline(topic, count, full_content)
            result.outline = outline
            result.pages = pages
            result.article = article_text  # 保存短文内容
            
            # 推送大纲结果（含详情）
            send_event('outline', {
                'outline': outline,
                'pages': [
                    {'index': p.index, 'page_type': p.page_type, 'content': p.content}
                    for p in pages
                ],
                'summary': f'共 {len(pages)} 页内容'
            })
            
            send_event('progress', {
                'stage': 'outline',
                'progress': 25,
                'message': f'大纲生成完成，共 {len(pages)} 页'
            })
            
            # ========== Step 3: 生成文案 ==========
            send_event('progress', {
                'stage': 'content',
                'progress': 28,
                'message': '正在生成文案内容...'
            })
            
            if is_cancelled():
                send_event('cancelled', {'message': '任务已被用户取消'})
                return
            
            content_result = await self._generate_content(topic, outline)
            result.titles = content_result.get('titles', [])
            result.copywriting = content_result.get('copywriting', '')
            result.tags = content_result.get('tags', [])
            
            # 推送文案结果
            send_event('content', {
                'titles': result.titles,
                'copywriting': result.copywriting,
                'tags': result.tags,
                'preview': result.copywriting[:100] + '...' if len(result.copywriting) > 100 else result.copywriting
            })
            
            send_event('progress', {
                'stage': 'content',
                'progress': 40,
                'message': '文案生成完成'
            })
            
            # ========== Step 4: 生成分镜/视觉指令 ==========
            visual_prompts = []
            if style == 'ghibli_summer':
                send_event('progress', {
                    'stage': 'storyboard',
                    'progress': 42,
                    'message': '正在设计分镜画面...'
                })
                
                if is_cancelled():
                    send_event('cancelled', {'message': '任务已被用户取消'})
                    return
                
                visual_prompts = await self._generate_all_visual_prompts(outline, len(pages), topic, result.article)
                
                # 推送分镜详情（完整视觉指令）
                send_event('storyboard', {
                    'prompts': [
                        {
                            'index': i,
                            'page_type': pages[i].page_type if i < len(pages) else 'content',
                            'prompt': vp  # 完整的视觉指令
                        }
                        for i, vp in enumerate(visual_prompts)
                    ],
                    'total': len(visual_prompts)
                })
                
                send_event('progress', {
                    'stage': 'storyboard',
                    'progress': 50,
                    'message': f'分镜设计完成，共 {len(visual_prompts)} 个画面'
                })
            else:
                send_event('progress', {
                    'stage': 'storyboard',
                    'progress': 50,
                    'message': '使用默认视觉风格'
                })
            
            # ========== Step 5: 生成图片 ==========
            if is_cancelled():
                send_event('cancelled', {'message': '任务已被用户取消'})
                return
            
            send_event('progress', {
                'stage': 'images',
                'progress': 52,
                'message': '正在生成图片...',
                'sub_progress': {'current': 0, 'total': len(pages)}
            })
            
            # 图片生成结果收集
            image_urls = [None] * len(pages)
            completed_images = 0
            
            # 创建带进度回调的图片生成任务
            async def generate_image_with_progress(page: XHSPage, visual_prompt: str = None):
                nonlocal completed_images
                
                # 发送开始生成事件
                send_event('image_progress', {
                    'index': page.index,
                    'progress': 0,
                    'status': 'generating',
                    'page_type': page.page_type
                })
                
                url = await self._generate_single_image_v2(
                    page, style, topic, outline, visual_prompt=visual_prompt
                )
                
                if url:
                    completed_images += 1
                    image_urls[page.index] = url
                    
                    # 推送单张图片完成
                    send_event('image', {
                        'index': page.index,
                        'url': url,
                        'page_type': page.page_type
                    })
                    
                    # 更新总进度
                    progress = 52 + int(35 * completed_images / len(pages))
                    send_event('progress', {
                        'stage': 'images',
                        'progress': progress,
                        'message': f'图片生成中 ({completed_images}/{len(pages)})',
                        'sub_progress': {'current': completed_images, 'total': len(pages)}
                    })
                else:
                    send_event('image_progress', {
                        'index': page.index,
                        'progress': 100,
                        'status': 'failed',
                        'page_type': page.page_type
                    })
                
                return url
            
            # 并行生成所有图片
            image_tasks = []
            for i, page in enumerate(pages):
                visual_prompt = visual_prompts[i] if i < len(visual_prompts) else None
                image_tasks.append(generate_image_with_progress(page, visual_prompt))
            
            await asyncio.gather(*image_tasks)
            
            # 过滤有效图片
            result.image_urls = [url for url in image_urls if url]
            
            send_event('progress', {
                'stage': 'images',
                'progress': 87,
                'message': f'图片生成完成，共 {len(result.image_urls)} 张'
            })
            
            # ========== Step 6: 生成动画封面 ==========
            video_url = None
            if generate_video and result.image_urls:
                if is_cancelled():
                    send_event('cancelled', {'message': '任务已被用户取消'})
                    return
                
                send_event('progress', {
                    'stage': 'video',
                    'progress': 88,
                    'message': '正在生成动画封面...'
                })
                
                video_url = await self._generate_video(result.image_urls[0])
                result.video_url = video_url
                
                if video_url:
                    send_event('video', {'url': video_url})
                
                send_event('progress', {
                    'stage': 'video',
                    'progress': 98,
                    'message': '动画封面生成完成'
                })
            else:
                send_event('progress', {
                    'stage': 'video',
                    'progress': 98,
                    'message': '跳过视频生成'
                })
            
            # ========== 保存结果 ==========
            try:
                from services.database_service import get_db_service
                db_service = get_db_service()
                if db_service:
                    db_service.save_xhs_record(
                        history_id=task_id,
                        topic=topic,
                        style=style,
                        image_urls=result.image_urls,
                        copy_text=result.copywriting,
                        hashtags=result.tags,
                        cover_image=result.image_urls[0] if result.image_urls else None,
                        cover_video=video_url
                    )
                    logger.info(f"小红书记录已保存: {task_id}")
            except Exception as e:
                logger.warning(f"保存小红书记录失败: {e}")
            
            # ========== 推送完成事件 ==========
            send_event('progress', {
                'stage': 'complete',
                'progress': 100,
                'message': '生成完成'
            })
            
            send_event('complete', {
                'id': task_id,
                'topic': result.topic,
                'style': result.style,
                'pages': [
                    {'index': p.index, 'page_type': p.page_type, 'content': p.content}
                    for p in result.pages
                ],
                'image_urls': result.image_urls,
                'video_url': result.video_url,
                'titles': result.titles,
                'copywriting': result.copywriting,
                'tags': result.tags,
                'outline': result.outline
            })
            
            logger.info(f"小红书系列生成完成: {task_id}, {len(result.image_urls)} 张图片")
            
        except Exception as e:
            logger.error(f"小红书生成失败: {e}", exc_info=True)
            send_event('error', {
                'message': str(e),
                'recoverable': False
            })


    async def generate_explanation_video(
        self,
        images: List[str],
        scripts: List[str],
        style: str = "ghibli_summer",
        target_duration: float = 60.0,
        bgm_url: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        video_model: str = "veo3"  # 视频模型: veo3 或 sora2
    ) -> Optional[str]:
        """
        从图片序列生成讲解视频
        
        Args:
            images: 小红书图片 URL 列表
            scripts: 每张图片的文案列表
            style: 动画风格（ghibli_summer/cartoon/scientific）
            target_duration: 目标总时长（秒）
            bgm_url: 背景音乐 URL（可选）
            progress_callback: 进度回调 callback(progress: int, status: str)
            video_model: 视频生成模型（sora2/veo3），默认 sora2
        
        Returns:
            最终视频 URL 或 None
        """
        from services.video_sequence_service import VideoSequenceOrchestrator
        
        logger.info(f"开始生成讲解视频: {len(images)} 张图片, 风格={style}, 目标时长={target_duration}s, 模型={video_model}")
        
        # 创建编排器
        orchestrator = VideoSequenceOrchestrator(
            llm_client=self.llm,
            video_service=self.video_service,
            prompt_manager=self.prompt_manager,
            oss_service=self.oss_service,
            video_model=video_model
        )
        
        # 执行编排
        video_url = await orchestrator.orchestrate(
            images=images,
            scripts=scripts,
            style=style,
            target_duration=target_duration,
            bgm_url=bgm_url,
            progress_callback=progress_callback,
            video_model=video_model
        )
        
        if video_url:
            logger.info(f"讲解视频生成成功: {video_url}")
        else:
            logger.error("讲解视频生成失败")
        
        return video_url


# 全局实例
_xhs_service: Optional[XHSService] = None


def init_xhs_service(
    llm_client,
    image_service=None,
    video_service=None,
    oss_service=None
) -> XHSService:
    """初始化小红书服务"""
    global _xhs_service
    _xhs_service = XHSService(
        llm_client=llm_client,
        image_service=image_service,
        video_service=video_service,
        oss_service=oss_service
    )
    return _xhs_service


def get_xhs_service() -> Optional[XHSService]:
    """获取小红书服务实例"""
    return _xhs_service
