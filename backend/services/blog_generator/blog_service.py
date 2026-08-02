"""
博客生成服务 - 封装 BlogGenerator，提供与 vibe-blog 集成的接口
"""

import logging
import threading
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from queue import Queue
from contextvars import copy_context

from logging_config import task_id_context
from infrastructure.paths import RuntimePaths

from .queue_bridge import update_queue_status, update_queue_progress
from .generator import BlogGenerator
from .lifecycle.result_pipeline import (
    GenerationResultPipeline,
    GenerationResultRequest,
)
from .lifecycle.progress_events import (
    normalize_research_result as _normalize_research_result,
    project_generation_event,
)
from .lifecycle.task_events import TaskEventBridge
from .schemas.state import create_initial_state
from .services.search_service import SearchService, init_search_service, get_search_service
from .post_processors.markdown_formatter import MarkdownFormatter

# 输出目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUTS_DIR = os.environ.get(
    "OUTPUT_FOLDER", str(RuntimePaths.from_env(project_root=PROJECT_ROOT).outputs)
)

logger = logging.getLogger(__name__)


# 全局博客生成服务实例
_blog_service: Optional['BlogService'] = None


class BlogService:
    """
    博客生成服务 - 与 vibe-blog 任务管理系统集成
    """
    
    def __init__(self, llm_client, search_service=None, knowledge_service=None):
        """
        初始化博客生成服务
        
        Args:
            llm_client: LLM 客户端
            search_service: 搜索服务 (可选)
            knowledge_service: 知识服务 (可选，用于文档知识融合)
        """
        self.knowledge_service = knowledge_service
        self.generator = BlogGenerator(
            llm_client=llm_client,
            search_service=search_service,
            knowledge_service=knowledge_service
        )
        self.generator.compile()
        self._result_pipeline = GenerationResultPipeline(self)

        # 101.113: 记录正在等待大纲确认的任务（用于 resume 时查找 config）
        self._interrupted_tasks: Dict[str, Dict] = {}  # task_id -> {config, task_manager, ...}

    def _get_token_usage(self) -> Optional[Dict]:
        """获取当前 token 用量摘要（用于注入 SSE 事件）"""
        if os.environ.get('SSE_TOKEN_SUMMARY_ENABLED', 'true').lower() == 'false':
            return None
        try:
            llm = self.generator.llm
            if hasattr(llm, 'token_tracker') and llm.token_tracker:
                return llm.token_tracker.get_summary()
        except Exception:
            pass
        return None

    @staticmethod
    def _validate_final_state(final_state: Dict) -> str:
        """Return generated Markdown or raise before any success side effects."""
        error = final_state.get('error')
        if error and str(error).strip():
            raise RuntimeError(str(error).strip())

        markdown = final_state.get('final_markdown')
        if not isinstance(markdown, str) or not markdown.strip():
            raise RuntimeError("博客生成未产生有效内容")
        return markdown

    def _send_completion_event(
        self, *, task_manager, task_id: str, final_state: Dict,
        markdown: str, saved_path: Optional[str],
        cover_video_path: Optional[str], citations: list,
    ) -> None:
        """Publish completion once the persisted article is readable."""
        if not task_manager:
            return

        complete_data = {
            'success': True,
            'id': task_id,
            'markdown': markdown,
            'outline': final_state.get('outline') or {},
            'sections_count': len(final_state.get('sections', [])),
            'images_count': len(final_state.get('images', [])),
            'code_blocks_count': len(final_state.get('code_blocks', [])),
            'review_score': final_state.get('review_score', 0),
            'saved_path': saved_path,
            'cover_video': cover_video_path,
            'citations': citations,
        }
        token_usage = self._get_token_usage()
        if token_usage:
            complete_data['token_usage'] = token_usage
        task_manager.send_event(task_id, 'complete', complete_data)
        update_queue_status(
            task_id,
            "completed",
            word_count=len(markdown),
            image_count=len(final_state.get('images', [])),
        )

    def enhance_topic(self, topic: str, timeout: float = 30.0) -> str:
        """
        使用 LLM 优化用户输入的主题（轻量直调，不走 resilient_chat 重试链）

        Args:
            topic: 用户原始输入
            timeout: 超时秒数（超时则返回原始 topic）

        Returns:
            优化后的主题字符串
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        from services.llm.service import _strip_thinking

        system_content = (
            "你是一个技术博客主题优化助手。用户会给你一个简短的技术关键词或主题，"
            "你需要将其扩展为一个具体、有吸引力的中文博客标题。\n\n"
            "规则：\n"
            "1. 保留用户的核心技术方向\n"
            "2. 补充具体的技术细节、应用场景或实战角度\n"
            "3. 标题长度 15-40 个字，适合深度技术博客\n"
            "4. 直接输出优化后的标题，不要加引号、不要解释、不要思考过程\n\n"
            "示例：\n"
            "输入: Redis\n"
            "输出: Redis 高并发场景下的缓存穿透与击穿解决方案\n\n"
            "输入: Vue3\n"
            "输出: Vue3 Composition API 实战：构建高性能中后台管理系统\n\n"
            "输入: LangChain\n"
            "输出: LangChain 实战指南：从零构建企业级 RAG 知识问答系统\n\n"
            "输入: Docker\n"
            "输出: Docker 容器化部署最佳实践：从开发到生产环境的完整方案"
        )
        langchain_messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"请优化以下主题：{topic}"),
        ]
        try:
            import concurrent.futures
            # 直接拿 LangChain model 实例，绕过 resilient_chat / 限流 / 心跳
            llm = self.generator.llm
            # LLMClientAdapter 包了一层，取底层 LLMService
            llm_service = getattr(llm, 'llm_service', llm)
            model = llm_service.get_text_model()
            if not model:
                logger.warning("[enhance_topic] 模型不可用，返回原始主题")
                return topic

            def _invoke():
                return model.invoke(langchain_messages)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_invoke)
                response = future.result(timeout=timeout)

            raw = response.content if response else ""
            logger.info(f"[enhance_topic] 原始主题: '{topic}', LLM 原始返回: '{raw[:200]}'")
            # 清理 <think> 标签
            cleaned = _strip_thinking(raw).strip().strip('"\'《》「」') if raw else ""
            if cleaned and cleaned.lower() != topic.lower():
                return cleaned
            logger.warning(f"[enhance_topic] 清理后结果与原始主题相同，返回原始主题")
        except concurrent.futures.TimeoutError:
            logger.warning(f"[enhance_topic] 超时({timeout}s)，返回原始主题")
        except Exception as e:
            logger.warning(f"[enhance_topic] 失败: {e}，返回原始主题")
        return topic

    def polish_selection(self, selected_text: str, instruction: str = "") -> str:
        """
        对用户选中的局部文本做轻量润色。

        Args:
            selected_text: 用户选中的原文
            instruction: 用户输入的润色目标

        Returns:
            润色后的文本；失败时返回原文
        """
        selected_text = (selected_text or "").strip()
        instruction = (instruction or "").strip()
        if not selected_text:
            return ""

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个中文技术写作润色助手。"
                    "你只处理用户给出的选中文本，不要扩写整篇文章，不要解释你的修改。"
                    "输出必须是可直接替换原文的纯文本，不要加引号，不要使用 markdown 代码块。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"润色目标：{instruction or '提升表达清晰度、流畅度与准确性'}\n\n"
                    f"待润色文本：\n{selected_text}\n\n"
                    "请只返回润色后的文本，保持原意。"
                ),
            },
        ]

        try:
            result = self.generator.llm.chat(messages, caller="polish_selection")
            if not result:
                return selected_text

            polished = result.strip()
            if polished.startswith("```") and polished.endswith("```"):
                lines = polished.splitlines()
                if len(lines) >= 3:
                    polished = "\n".join(lines[1:-1]).strip()
            return polished or selected_text
        except Exception as e:
            logger.warning(f"文本润色失败，返回原文: {e}")
            return selected_text

    def _get_flask_app(self):
        """安全获取当前 Flask app 引用（用于 resume 线程）"""
        try:
            from flask import current_app
            return current_app._get_current_object()
        except Exception:
            return None

    def confirm_outline(self, task_id: str, action: str = 'accept', outline: dict = None) -> bool:
        """
        确认大纲（兼容旧接口，内部转发到 resume_generation）

        Args:
            task_id: 任务 ID
            action: 'accept' 或 'edit'
            outline: 修改后的大纲（仅 action='edit' 时需要）

        Returns:
            是否成功
        """
        return self.resume_generation(task_id, action=action, outline=outline)

    def resume_generation(self, task_id: str, action: str = 'accept', outline: dict = None) -> bool:
        """
        恢复中断的生成任务（101.113 LangGraph interrupt 方案）

        在后台线程中使用 Command(resume=...) 恢复图执行。

        Args:
            task_id: 任务 ID
            action: 'accept' 或 'edit'
            outline: 修改后的大纲（仅 action='edit' 时需要）

        Returns:
            是否成功启动恢复
        """
        task_info = self._interrupted_tasks.get(task_id)
        if not task_info:
            logger.warning(f"resume_generation: 任务 {task_id} 不在中断列表中")
            return False

        # 构建 resume 值
        if action == 'edit' and outline:
            resume_value = {"action": "edit", "outline": outline}
        else:
            resume_value = "accept"

        # 在后台线程中恢复执行
        def run_resume():
            from langgraph.types import Command
            token = task_id_context.set(task_id)
            try:
                config = task_info['config']
                task_manager = task_info.get('task_manager')
                app_ctx = task_info.get('app')

                if app_ctx:
                    with app_ctx.app_context():
                        self._run_resume(
                            task_id=task_id,
                            resume_value=resume_value,
                            config=config,
                            task_manager=task_manager,
                            task_info=task_info,
                        )
                else:
                    self._run_resume(
                        task_id=task_id,
                        resume_value=resume_value,
                        config=config,
                        task_manager=task_manager,
                        task_info=task_info,
                    )
            finally:
                task_id_context.reset(token)
                self._interrupted_tasks.pop(task_id, None)

        ctx = copy_context()
        thread = threading.Thread(target=ctx.run, args=(run_resume,), daemon=True)
        thread.start()
        return True

    def evaluate_article(self, content: str, title: str = '', article_type: str = '') -> Dict[str, Any]:
        """
        评估文章质量（基础统计 + LLM 评分）

        Args:
            content: 文章 Markdown 内容
            title: 文章标题
            article_type: 文章类型

        Returns:
            评估结果字典
        """
        import re

        # 基础统计（不依赖 LLM）
        word_count = len(content)
        citation_count = len(re.findall(r'\[.*?\]\(https?://.*?\)', content))
        image_count = len(re.findall(r'!\[.*?\]\(.*?\)', content))
        code_block_count = len(re.findall(r'```[\s\S]*?```', content))

        base_result = {
            'word_count': word_count,
            'citation_count': citation_count,
            'image_count': image_count,
            'code_block_count': code_block_count,
        }

        # LLM 评估
        try:
            messages = [
                {"role": "system", "content": "你是一个专业的文章质量评估专家。请对以下文章进行评估，返回 JSON 格式结果。"},
                {"role": "user", "content": f"""请评估以下文章的质量，返回严格 JSON 格式：

标题：{title}
类型：{article_type}

文章内容（前 3000 字）：
{content[:3000]}

请返回以下 JSON 格式（不要包含 markdown 代码块标记）：
{{
  "overall_score": 0-100 的整数,
  "grade": "A+/A/A-/B+/B/B-/C+/C/C-/D/F 之一",
  "scores": {{
    "factual_accuracy": 0-100,
    "completeness": 0-100,
    "coherence": 0-100,
    "relevance": 0-100,
    "citation_quality": 0-100,
    "writing_quality": 0-100
  }},
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1"],
  "suggestions": ["建议1"],
  "summary": "一句话总结"
}}"""},
            ]
            import json
            result = self.generator.llm.chat(
                messages,
                response_format={"type": "json_object"},
                caller="evaluate_article"
            )
            if result:
                evaluation = json.loads(result)
                evaluation.update(base_result)
                return evaluation
        except Exception as e:
            logger.warning(f"LLM 评估失败，降级为基础统计: {e}")

        # 降级结果
        return {
            **base_result,
            'grade': 'N/A',
            'overall_score': 0,
            'scores': {
                'factual_accuracy': 0, 'completeness': 0, 'coherence': 0,
                'relevance': 0, 'citation_quality': 0, 'writing_quality': 0,
            },
            'strengths': [], 'weaknesses': [], 'suggestions': [],
            'summary': 'LLM 评估不可用，仅提供基础统计',
        }

    def generate_sync(
        self,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        target_length: str = "medium",
        source_material: str = None
    ) -> Dict[str, Any]:
        """
        同步生成博客
        
        Args:
            topic: 技术主题
            article_type: 文章类型
            target_audience: 目标受众
            target_length: 目标长度
            source_material: 参考资料
            
        Returns:
            生成结果
        """
        return self.generator.generate(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material
        )
    
    def generate_async(
        self,
        task_id: str,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        audience_adaptation: str = "default",
        target_length: str = "medium",
        source_material: str = None,
        document_ids: list = None,
        document_knowledge: list = None,
        image_style: str = "",
        generate_images: bool = True,
        generate_cover_video: bool = False,
        video_aspect_ratio: str = "16:9",
        custom_config: dict = None,
        deep_thinking: bool = False,
        background_investigation: bool = True,
        interactive: bool = False,
        task_manager=None,
        app=None
    ):
        """
        异步生成博客 (在后台线程执行)
        
        Args:
            task_id: 任务 ID
            topic: 技术主题
            article_type: 文章类型
            target_audience: 目标受众
            audience_adaptation: 受众适配类型 (default/high-school/children/professional)
            target_length: 目标长度 (mini/short/medium/long/custom)
            source_material: 参考资料
            document_ids: 文档 ID 列表
            document_knowledge: 文档知识列表
            image_style: 图片风格 ID
            generate_images: 是否生成章节图和封面图
            generate_cover_video: 是否生成封面动画
            custom_config: 自定义配置（仅当 target_length='custom' 时使用）
            deep_thinking: 是否启用深度思考模式
            background_investigation: 是否启用背景调查（搜索）
            interactive: 是否交互式模式（大纲确认后再写作）
            task_manager: 任务管理器
            app: Flask 应用实例
        """
        def run_in_thread():
            # 在线程中设置 task_id 上下文
            token = task_id_context.set(task_id)
            
            try:
                if app:
                    with app.app_context():
                        self._run_generation(
                            task_id=task_id,
                            topic=topic,
                            article_type=article_type,
                            target_audience=target_audience,
                            audience_adaptation=audience_adaptation,
                            target_length=target_length,
                            source_material=source_material,
                            document_ids=document_ids,
                            document_knowledge=document_knowledge,
                            image_style=image_style,
                            generate_images=generate_images,
                            generate_cover_video=generate_cover_video,
                            video_aspect_ratio=video_aspect_ratio,
                            custom_config=custom_config,
                            deep_thinking=deep_thinking,
                            background_investigation=background_investigation,
                            interactive=interactive,
                            task_manager=task_manager
                        )
                else:
                    self._run_generation(
                        task_id=task_id,
                        topic=topic,
                        article_type=article_type,
                        target_audience=target_audience,
                        audience_adaptation=audience_adaptation,
                        target_length=target_length,
                        source_material=source_material,
                        document_ids=document_ids,
                        document_knowledge=document_knowledge,
                        image_style=image_style,
                        generate_images=generate_images,
                        generate_cover_video=generate_cover_video,
                        video_aspect_ratio=video_aspect_ratio,
                        custom_config=custom_config,
                        deep_thinking=deep_thinking,
                        background_investigation=background_investigation,
                        interactive=interactive,
                        task_manager=task_manager
                    )
            finally:
                # 重置上下文
                task_id_context.reset(token)
        
        # 使用 copy_context 确保线程继承当前上下文
        ctx = copy_context()
        thread = threading.Thread(target=ctx.run, args=(run_in_thread,), daemon=True)
        thread.start()
    
    def _run_generation(
        self,
        task_id: str,
        topic: str,
        article_type: str,
        target_audience: str,
        audience_adaptation: str,
        target_length: str,
        source_material: str,
        document_ids: list = None,
        document_knowledge: list = None,
        image_style: str = "",
        generate_images: bool = True,
        generate_cover_video: bool = False,
        video_aspect_ratio: str = "16:9",
        custom_config: dict = None,
        deep_thinking: bool = False,
        background_investigation: bool = True,
        interactive: bool = False,
        task_manager=None
    ):
        """
        执行生成流程，发送 SSE 事件
        """
        import time
        event_bridge = TaskEventBridge(self.generator, task_manager, task_id)
        sse_handler = event_bridge.attach()
        sse_logger_names = event_bridge.logger_names

        # 等待 SSE 连接建立
        time.sleep(0.5)
        event_bridge.inject_dependencies()

        # 创建 Token 追踪器（37.31）
        token_tracker = None
        try:
            if os.environ.get('TOKEN_TRACKING_ENABLED', 'true').lower() == 'true':
                from utils.token_tracker import TokenTracker
                token_tracker = TokenTracker()
                self.generator.llm.token_tracker = token_tracker
        except Exception:
            pass

        # 创建结构化任务日志（37.08）
        task_log = None
        try:
            if os.environ.get('BLOG_TASK_LOG_ENABLED', 'true').lower() == 'true':
                from .utils.task_log import BlogTaskLog
                task_log = BlogTaskLog(
                    task_id=task_id,
                    topic=topic,
                    article_type=article_type,
                    target_length=target_length,
                )
                self.generator.task_log = task_log
                # 注入到中间件，自动记录每个节点耗时
                if hasattr(self.generator, '_task_log_middleware'):
                    self.generator._task_log_middleware.set_task_log(task_log)
        except Exception:
            pass

        # 创建按任务分离的文本日志
        task_log_handler = None
        try:
            from logging_config import create_task_logger
            task_log_handler = create_task_logger(task_id)
        except Exception:
            pass

        try:
            # 发送开始事件
            if task_manager:
                task_manager.send_event(task_id, 'progress', {
                    'stage': 'start',
                    'progress': 0,
                    'message': f'开始生成博客: {topic}'
                })
            
            # 获取文章长度配置
            from config import get_article_config
            article_config = get_article_config(target_length, custom_config).copy()
            if not generate_images:
                article_config['images_count'] = 0
            logger.info(f"文章配置: sections={article_config['sections_count']}, "
                        f"images={article_config['images_count']}, "
                        f"code_blocks={article_config['code_blocks_count']}, "
                        f"words={article_config['target_word_count']}")
            
            # 创建初始状态（支持文档知识、图片风格、文章长度配置和宽高比）
            initial_state = create_initial_state(
                topic=topic,
                article_type=article_type,
                target_audience=target_audience,
                audience_adaptation=audience_adaptation,
                target_length=target_length,
                source_material=source_material,
                document_ids=document_ids or [],
                document_knowledge=document_knowledge or [],
                image_style=image_style,
                aspect_ratio=video_aspect_ratio,  # 新增：传递宽高比
                custom_config=custom_config,
                target_sections_count=article_config['sections_count'],
                target_images_count=article_config['images_count'],
                target_code_blocks_count=article_config['code_blocks_count'],
                target_word_count=article_config['target_word_count']
            )
            
            # 注意：不要将函数放入 state，会导致 LangGraph checkpoint 序列化失败
            # 取消检查已在主循环中处理 (line 272)
            
            # deep_thinking: 设置 LLM thinking mode（更深入推理，生成时间更长）
            if deep_thinking:
                try:
                    self.generator.llm.thinking_enabled = True
                    logger.info(f"深度思考模式已启用 [{task_id}]")
                except Exception:
                    logger.warning("LLM 不支持 thinking mode，忽略 deep_thinking 参数")
            
            # background_investigation=false: 跳过 researcher，直接从 planner 开始
            if not background_investigation:
                initial_state['skip_researcher'] = True
                if task_manager:
                    task_manager.send_event(task_id, 'progress', {
                        'stage': 'researcher_skipped',
                        'progress': 15,
                        'message': '已跳过背景调查，直接开始规划'
                    })
                logger.info(f"背景调查已跳过 [{task_id}]")
            
            # 设置大纲流式回调到 generator 实例
            def on_outline_stream(delta, accumulated):
                if task_manager:
                    task_manager.send_event(task_id, 'stream', {
                        'stage': 'outline',
                        'delta': delta,
                        'accumulated': accumulated
                    })
            
            self.generator._configure_planner_runtime(
                on_stream=on_outline_stream,
                interactive=interactive,
            )
            
            config = {"configurable": {"thread_id": f"blog_{task_id}"}}
            
            # 注入 Langfuse 追踪回调（如果已启用）
            # 每个任务创建独立 handler，设置 session_id 使同一任务的 trace 归组
            try:
                import os as _os
                if _os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
                    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
                    langfuse_handler = LangfuseCallbackHandler(
                        session_id=task_id,
                        trace_name=f"blog-gen-{topic[:30]}",
                        metadata={"task_id": task_id, "topic": topic,
                                  "article_type": article_type, "target_length": target_length},
                    )
                    config["callbacks"] = [langfuse_handler]
            except Exception:
                pass
            
            # 记录已完成的章节数
            completed_sections = 0

            # 根据 StyleProfile 配置并行执行引擎
            from .style_profile import StyleProfile
            from .parallel import ParallelTaskExecutor
            style = StyleProfile.from_target_length(target_length)
            self.generator._configure_execution_runtime(
                ParallelTaskExecutor(enable_parallel=style.enable_parallel)
            )

            # 使用 stream 获取中间状态
            for event in self.generator.app.stream(initial_state, config):
                # 检查任务是否被取消
                if task_manager and task_manager.is_cancelled(task_id):
                    logger.info(f"任务已取消，停止生成: {task_id}")
                    self._interrupted_tasks.pop(task_id, None)
                    task_manager.send_event(task_id, 'cancelled', {
                        'task_id': task_id,
                        'message': '任务已被用户取消'
                    })
                    return
                
                for node_name, state in event.items():
                    token_usage = (
                        self._get_token_usage() if task_manager else None
                    )
                    completed_sections = project_generation_event(
                        task_manager=task_manager,
                        task_id=task_id,
                        node_name=node_name,
                        state=state,
                        completed_sections=completed_sections,
                        interactive=interactive,
                        token_usage=token_usage,
                        initial_generation=True,
                        update_queue_progress_fn=update_queue_progress,
                    )
            
            # 101.113: 检查是否因 interrupt 暂停（交互式大纲确认）
            snapshot = self.generator.app.get_state(config)
            if snapshot.next:  # 图还有未完成的节点 → 被 interrupt 暂停了
                logger.info(f"图执行被 interrupt 暂停，等待用户确认大纲 [{task_id}]")
                # 提取 interrupt 数据
                interrupt_value = None
                if snapshot.tasks:
                    for task in snapshot.tasks:
                        if hasattr(task, 'interrupts') and task.interrupts:
                            interrupt_value = task.interrupts[0].value
                            break

                # 发送 outline_ready 事件
                if task_manager and interrupt_value and interrupt_value.get('type') == 'confirm_outline':
                    task_manager.send_event(task_id, 'outline_ready', {
                        'title': interrupt_value.get('title', ''),
                        'sections': interrupt_value.get('sections', []),
                        'sections_titles': interrupt_value.get('sections_titles', []),
                    })

                # 保存任务信息，供 resume_generation 使用
                self._interrupted_tasks[task_id] = {
                    'config': config,
                    'task_manager': task_manager,
                    'app': self._get_flask_app(),  # Flask app 引用，供 resume 线程使用
                    'topic': topic,
                    'article_type': article_type,
                    'target_length': target_length,
                    'interactive': interactive,
                    'generate_images': generate_images,
                    'generate_cover_video': generate_cover_video,
                    'video_aspect_ratio': video_aspect_ratio,
                    'article_config': article_config,
                    'token_tracker': token_tracker,
                    'task_log': task_log,
                    'event_bridge': event_bridge,
                    'sse_handler': sse_handler,
                    'sse_logger_names': sse_logger_names,
                }
                # 不清理日志处理器，resume 时还需要
                _interrupted = True
                return

            final_state = snapshot.values
            result_pipeline = getattr(self, "_result_pipeline", None)
            if result_pipeline is None:
                result_pipeline = GenerationResultPipeline(self)
            result = result_pipeline.finalize(
                GenerationResultRequest(
                    task_id=task_id,
                    topic=topic,
                    article_type=article_type,
                    target_length=target_length,
                    final_state=final_state,
                    article_config=article_config,
                    generate_images=generate_images,
                    generate_cover_video=generate_cover_video,
                    video_aspect_ratio=video_aspect_ratio,
                    task_manager=task_manager,
                    token_tracker=token_tracker,
                    task_log=task_log,
                    record_memory=True,
                )
            )
            logger.info(f"博客生成完成: {task_id}, 保存到: {result.saved_path}")

        except Exception as e:
            logger.error(f"博客生成失败 [{task_id}]: {e}", exc_info=True)
            if task_log:
                try:
                    task_log.fail(str(e))
                    task_log.save()
                except Exception:
                    pass
            if task_manager:
                task_manager.send_event(task_id, 'error', {
                    'message': str(e),
                    'recoverable': False
                })
            update_queue_status(task_id, "failed", error_msg=str(e))
        finally:
            # 清理日志处理器（interrupt 暂停时不清理，留给 _run_resume）
            if not locals().get('_interrupted'):
                event_bridge.close()
            # 清理按任务分离的文本日志 handler
            if task_log_handler and not locals().get('_interrupted'):
                from logging_config import remove_task_logger
                remove_task_logger(task_log_handler)
    
    def _run_resume(
        self,
        task_id: str,
        resume_value,
        config: dict,
        task_manager=None,
        task_info: dict = None,
    ):
        """
        101.113: 恢复中断的图执行（Command(resume=...)），然后执行后处理。

        复用 _run_generation 中 stream 循环后的逻辑（封面图、保存历史等）。
        """
        import time
        import logging
        from langgraph.types import Command

        task_info = task_info or {}
        topic = task_info.get('topic', '')
        article_type = task_info.get('article_type', 'tutorial')
        target_length = task_info.get('target_length', 'medium')
        interactive = task_info.get('interactive', False)
        generate_images = task_info.get('generate_images', True)
        generate_cover_video = task_info.get('generate_cover_video', False)
        video_aspect_ratio = task_info.get('video_aspect_ratio', '16:9')

        # 创建按任务分离的文本日志（resume 阶段继续写入同一任务文件夹）
        task_log_handler = None
        try:
            from logging_config import create_task_logger
            task_log_handler = create_task_logger(task_id)
        except Exception:
            pass
        article_config = task_info.get('article_config', {})
        token_tracker = task_info.get('token_tracker')
        task_log = task_info.get('task_log')
        event_bridge = task_info.get('event_bridge')
        sse_handler = task_info.get('sse_handler')
        sse_logger_names = task_info.get('sse_logger_names', [])

        # 发送确认事件
        if task_manager:
            if isinstance(resume_value, dict) and resume_value.get('action') == 'edit':
                task_manager.send_event(task_id, 'progress', {
                    'stage': 'outline_edited',
                    'message': '大纲已修改，开始写作'
                })
            else:
                task_manager.send_event(task_id, 'progress', {
                    'stage': 'outline_confirmed',
                    'message': '大纲已确认，开始写作'
                })

        completed_sections = 0

        # 102.07: 修复悬挂工具调用（防御性代码，防止 resume 时消息历史不完整）
        try:
            snapshot = self.generator.app.get_state(config)
            if snapshot and snapshot.values:
                for key in ('messages', 'chat_history'):
                    msgs = snapshot.values.get(key, [])
                    if msgs:
                        from utils.dangling_tool_call_fixer import fix_dangling_tool_calls
                        patches = fix_dangling_tool_calls(msgs)
                        if patches:
                            logger.info(f"[resume] 修复 {len(patches)} 个悬挂工具调用")
                            self.generator.app.update_state(config, {key: msgs + patches})
        except Exception as e:
            logger.debug(f"悬挂工具调用检查跳过: {e}")

        try:
            # 使用 Command(resume=...) 恢复图执行
            for event in self.generator.app.stream(Command(resume=resume_value), config):
                # 检查任务是否被取消
                if task_manager and task_manager.is_cancelled(task_id):
                    logger.info(f"任务已取消，停止生成: {task_id}")
                    task_manager.send_event(task_id, 'cancelled', {
                        'task_id': task_id,
                        'message': '任务已被用户取消'
                    })
                    return

                for node_name, state in event.items():
                    token_usage = (
                        self._get_token_usage() if task_manager else None
                    )
                    completed_sections = project_generation_event(
                        task_manager=task_manager,
                        task_id=task_id,
                        node_name=node_name,
                        state=state,
                        completed_sections=completed_sections,
                        interactive=interactive,
                        token_usage=token_usage,
                        initial_generation=False,
                        update_queue_progress_fn=update_queue_progress,
                    )

            final_state = self.generator.app.get_state(config).values
            result_pipeline = getattr(self, "_result_pipeline", None)
            if result_pipeline is None:
                result_pipeline = GenerationResultPipeline(self)
            result = result_pipeline.finalize(
                GenerationResultRequest(
                    task_id=task_id,
                    topic=topic,
                    article_type=article_type,
                    target_length=target_length,
                    final_state=final_state,
                    article_config=article_config,
                    generate_images=generate_images,
                    generate_cover_video=generate_cover_video,
                    video_aspect_ratio=video_aspect_ratio,
                    task_manager=task_manager,
                    token_tracker=token_tracker,
                    task_log=task_log,
                )
            )
            logger.info(
                f"博客生成完成（resume）: {task_id}, 保存到: {result.saved_path}"
            )
        except Exception as e:
            logger.error(f"博客生成失败（resume）[{task_id}]: {e}", exc_info=True)
            if task_log:
                try:
                    task_log.fail(str(e))
                    task_log.save()
                except Exception:
                    pass
            if task_manager:
                task_manager.send_event(task_id, 'error', {
                    'message': str(e),
                    'recoverable': False
                })
            update_queue_status(task_id, "failed", error_msg=str(e))
        finally:
            if event_bridge:
                event_bridge.close()
            elif sse_handler:
                for logger_name in sse_logger_names:
                    logging.getLogger(logger_name).removeHandler(sse_handler)
            # 清理按任务分离的文本日志 handler
            if task_log_handler:
                from logging_config import remove_task_logger
                remove_task_logger(task_log_handler)

    def _save_markdown(
        self,
        task_id: str,
        markdown: str,
        outline: Dict[str, Any],
        cover_image_path: Optional[str] = None
    ) -> Optional[str]:
        """
        保存 Markdown 到文件
        
        Args:
            task_id: 任务 ID
            markdown: Markdown 内容
            outline: 大纲信息
            cover_image_path: 封面图路径
            
        Returns:
            保存的文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(OUTPUTS_DIR, exist_ok=True)
            
            # 生成文件名
            title = outline.get('title', 'blog')
            # 清理标题中的特殊字符
            safe_title = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in title)[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_title}_{timestamp}.md"
            
            filepath = os.path.join(OUTPUTS_DIR, filename)
            
            # 如果有封面图，在 Markdown 开头插入
            final_markdown = markdown
            if cover_image_path:
                # 获取相对路径或文件名
                cover_filename = os.path.basename(cover_image_path)
                # 图片统一放在 outputs/images/ 目录下
                cover_section = f"""
![{title} - 架构图](./images/{cover_filename})

*{title} - 系统架构概览*

---

"""
                # 在标题后插入封面图
                # 找到第一个 ## 之前的位置插入
                lines = markdown.split('\n')
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('## ') and i > 0:
                        insert_idx = i
                        break
                
                if insert_idx > 0:
                    lines.insert(insert_idx, cover_section)
                    final_markdown = '\n'.join(lines)
                else:
                    # 如果没找到，就在开头插入
                    final_markdown = cover_section + markdown
            
            # 写入文件（102.07 原子写入，防止崩溃时产生半写文件）
            from utils.atomic_write import atomic_write
            atomic_write(filepath, final_markdown)
            
            # 后处理：修复分割线前后的换行符
            try:
                formatter = MarkdownFormatter()
                formatter.process_file(filepath)
                logger.info(f"Markdown 格式化完成: {filepath}")
            except Exception as format_error:
                logger.warning(f"Markdown 格式化失败（非致命错误）: {format_error}")
            
            logger.info(f"Markdown 已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存 Markdown 失败: {e}")
            return None


def init_blog_service(llm_client, search_service=None, knowledge_service=None) -> BlogService:
    """
    初始化博客生成服务
    
    Args:
        llm_client: LLM 客户端 (banana-blog 的 LLMService)
        search_service: 搜索服务 (智谱搜索)
        knowledge_service: 知识服务 (可选，用于文档知识融合)
        
    Returns:
        BlogService 实例
    """
    global _blog_service
    
    # 创建 LLM 客户端适配器
    llm_adapter = LLMClientAdapter(llm_client)
    
    _blog_service = BlogService(llm_adapter, search_service, knowledge_service)
    logger.info("博客生成服务已初始化")
    return _blog_service


class LLMClientAdapter:
    """
    LLM 客户端适配器 - 将 banana-blog 的 LLMService 适配为 BlogGenerator 需要的接口
    """
    
    def __init__(self, llm_service):
        """
        初始化适配器

        Args:
            llm_service: banana-blog 的 LLMService
        """
        self.llm_service = llm_service

    @property
    def token_tracker(self):
        return self.llm_service.token_tracker

    @token_tracker.setter
    def token_tracker(self, value):
        self.llm_service.token_tracker = value
    
    def chat(self, messages, response_format=None, caller: str = "", **kwargs):
        """
        调用 LLM 进行对话

        Args:
            messages: 消息列表
            response_format: 响应格式 (可选)，如 {"type": "json_object"}
            caller: 调用方标识 (可选)，用于日志追踪
            **kwargs: 透传给 LLMService 的额外参数 (tier, thinking, thinking_budget 等)

        Returns:
            LLM 响应文本
        """
        result = self.llm_service.chat(
            messages, response_format=response_format, caller=caller, **kwargs
        )

        if result:
            return result
        else:
            raise Exception('LLM 调用失败')

    def chat_stream(self, messages, on_chunk=None, response_format=None, **kwargs):
        """
        流式调用 LLM 进行对话

        Args:
            messages: 消息列表
            on_chunk: 每收到一个 chunk 时的回调函数 (delta, accumulated)
            response_format: 响应格式 (可选)，如 {"type": "json_object"}
            **kwargs: 透传给 LLMService 的额外参数 (tier, temperature, caller 等)

        Returns:
            完整的 LLM 响应文本
        """
        if hasattr(self.llm_service, 'chat_stream'):
            result = self.llm_service.chat_stream(
                messages, on_chunk=on_chunk, response_format=response_format, **kwargs
            )
            if result:
                return result
            else:
                raise Exception('LLM 流式调用失败')
        else:
            # 降级为普通调用
            return self.chat(messages, response_format=response_format, **kwargs)


def get_blog_service() -> Optional[BlogService]:
    """获取博客生成服务实例"""
    return _blog_service


def extract_article_summary(llm_client, title: str, content: str, max_length: int = 500) -> str:
    """
    提炼文章摘要（统一的摘要生成函数）
    
    使用 article_summary.j2 模板，供博客生成和书籍扫描服务共同调用
    
    Args:
        llm_client: LLM 客户端
        title: 文章标题
        content: 文章内容（Markdown）
        max_length: 摘要最大长度（默认500字）
        
    Returns:
        提炼后的摘要文本
    """
    if not content:
        return f"标题：{title}"
    
    if not llm_client:
        # 无 LLM 时，使用简单截取
        clean_content = content.replace('#', '').replace('*', '').replace('`', '')[:max_length]
        return clean_content.strip()
    
    # 限制输入长度，避免超出 token 限制
    content_for_summary = content[:18000] if len(content) > 18000 else content
    
    # 使用统一的 article_summary.j2 模板，在 Prompt 中限定字数
    from services.blog_generator.prompts import get_prompt_manager
    summary_prompt = get_prompt_manager().render_article_summary(title, content_for_summary, max_length=max_length)

    try:
        response = llm_client.chat(messages=[{"role": "user", "content": summary_prompt}])
        response_text = response if isinstance(response, str) else response.get('content', '')
        
        if response_text:
            return response_text.strip()
        else:
            # 降级：使用简单截取
            clean_content = content.replace('#', '').replace('*', '').replace('`', '')[:500]
            return clean_content.strip()
    except Exception as e:
        logging.getLogger(__name__).warning(f"LLM 生成摘要失败: {e}")
        # 降级：使用简单截取
        clean_content = content.replace('#', '').replace('*', '').replace('`', '')[:500]
        return clean_content.strip()
