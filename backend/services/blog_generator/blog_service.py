"""
博客生成服务 - 封装 BlogGenerator，提供与 vibe-blog 集成的接口
"""

import logging
import threading
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from queue import Queue
from contextvars import copy_context

from .generator import BlogGenerator
from .schemas.state import create_initial_state
from .services.search_service import SearchService, init_search_service, get_search_service
from .post_processors.markdown_formatter import MarkdownFormatter
from ..image_service import get_image_service, AspectRatio, ImageSize

# 输出目录
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs')

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
        generate_cover_video: bool = False,
        custom_config: dict = None,
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
            generate_cover_video: 是否生成封面动画
            custom_config: 自定义配置（仅当 target_length='custom' 时使用）
            task_manager: 任务管理器
            app: Flask 应用实例
        """
        def run_in_thread():
            # 导入 task_id_context
            from app import task_id_context
            
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
                            generate_cover_video=generate_cover_video,
                            custom_config=custom_config,
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
                        generate_cover_video=generate_cover_video,
                        custom_config=custom_config,
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
        generate_cover_video: bool = False,
        custom_config: dict = None,
        task_manager=None
    ):
        """
        执行生成流程，发送 SSE 事件
        """
        import time
        import logging
        
        # 创建一个自定义日志处理器，将日志推送到前端
        class SSELogHandler(logging.Handler):
            def __init__(self, task_manager, task_id):
                super().__init__()
                self.task_manager = task_manager
                self.task_id = task_id
                
            def emit(self, record):
                if self.task_manager and record.name.startswith('services.blog_generator'):
                    msg = self.format(record)
                    self.task_manager.send_event(self.task_id, 'log', {
                        'level': record.levelname,
                        'logger': record.name.split('.')[-1],
                        'message': msg
                    })
        
        # 添加日志处理器
        sse_handler = None
        if task_manager:
            sse_handler = SSELogHandler(task_manager, task_id)
            sse_handler.setLevel(logging.INFO)
            sse_handler.setFormatter(logging.Formatter('%(message)s'))
            
            # 给所有 blog_generator 相关的 logger 添加处理器
            for logger_name in [
                'services.blog_generator.generator',
                'services.blog_generator.agents.researcher',
                'services.blog_generator.agents.planner',
                'services.blog_generator.agents.writer',
                'services.blog_generator.agents.questioner',
                'services.blog_generator.agents.coder',
                'services.blog_generator.agents.artist',
                'services.blog_generator.agents.reviewer',
                'services.blog_generator.agents.assembler',
                'services.blog_generator.agents.search_coordinator',
                'services.blog_generator.services.search_service',
                'services.image_service',
            ]:
                logging.getLogger(logger_name).addHandler(sse_handler)
        
        # 等待 SSE 连接建立
        time.sleep(0.5)
        
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
            article_config = get_article_config(target_length, custom_config)
            logger.info(f"文章配置: sections={article_config['sections_count']}, "
                        f"images={article_config['images_count']}, "
                        f"code_blocks={article_config['code_blocks_count']}, "
                        f"words={article_config['target_word_count']}")
            
            # 创建初始状态（支持文档知识、图片风格和文章长度配置）
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
                custom_config=custom_config,
                target_sections_count=article_config['sections_count'],
                target_images_count=article_config['images_count'],
                target_code_blocks_count=article_config['code_blocks_count'],
                target_word_count=article_config['target_word_count']
            )
            
            # 注意：不要将函数放入 state，会导致 LangGraph checkpoint 序列化失败
            # 取消检查已在主循环中处理 (line 272)
            
            # 设置大纲流式回调到 generator 实例
            def on_outline_stream(delta, accumulated):
                if task_manager:
                    task_manager.send_event(task_id, 'stream', {
                        'stage': 'outline',
                        'delta': delta,
                        'accumulated': accumulated
                    })
            
            self.generator._outline_stream_callback = on_outline_stream
            
            config = {"configurable": {"thread_id": f"blog_{task_id}"}}
            
            # 阶段进度映射
            stage_progress = {
                'researcher': (10, '正在搜索资料...'),
                'planner': (25, '正在生成大纲...'),
                'writer': (45, '正在撰写内容...'),
                # 多轮搜索相关节点
                'check_knowledge': (52, '正在检查知识空白...'),
                'refine_search': (54, '正在补充搜索...'),
                'enhance_with_knowledge': (56, '正在增强内容...'),
                # 追问和后续节点
                'questioner': (60, '正在检查内容深度...'),
                'deepen_content': (65, '正在深化内容...'),
                'coder': (75, '正在生成代码示例...'),
                'artist': (85, '正在生成配图...'),
                'reviewer': (92, '正在审核质量...'),
                'revision': (95, '正在修订内容...'),
                'assembler': (98, '正在组装文档...'),
            }
            
            # 记录已完成的章节数
            completed_sections = 0
            
            # 使用 stream 获取中间状态
            for event in self.generator.app.stream(initial_state, config):
                # 检查任务是否被取消
                if task_manager and task_manager.is_cancelled(task_id):
                    logger.info(f"任务已取消，停止生成: {task_id}")
                    task_manager.send_event(task_id, 'cancelled', {
                        'task_id': task_id,
                        'message': '任务已被用户取消'
                    })
                    return
                
                for node_name, state in event.items():
                    progress_info = stage_progress.get(node_name, (50, f'正在执行 {node_name}...'))
                    
                    if task_manager:
                        # 发送阶段进度
                        task_manager.send_event(task_id, 'progress', {
                            'stage': node_name,
                            'progress': progress_info[0],
                            'message': progress_info[1]
                        })
                        
                        # 发送详细中间结果
                        if node_name == 'researcher':
                            # 素材收集结果
                            background = state.get('background_knowledge', '')
                            key_concepts = state.get('key_concepts', [])
                            knowledge_stats = state.get('knowledge_source_stats', {})
                            
                            # 准备文档知识预览（前500字）
                            doc_knowledge = state.get('document_knowledge', [])
                            doc_previews = []
                            for doc in doc_knowledge[:3]:  # 最多展示3个文档
                                content = doc.get('content', '')
                                preview = content[:500] + '...' if len(content) > 500 else content
                                doc_previews.append({
                                    'file_name': doc.get('file_name', '未知文档'),
                                    'preview': preview,
                                    'total_length': len(content)
                                })
                            
                            task_manager.send_event(task_id, 'result', {
                                'type': 'researcher_complete',
                                'data': {
                                    'background_length': len(background),
                                    'key_concepts': key_concepts[:5] if key_concepts else [],
                                    'document_count': knowledge_stats.get('document_count', 0),
                                    'web_count': knowledge_stats.get('web_count', 0),
                                    'document_previews': doc_previews,
                                    'message': f'素材收集完成，获取 {len(background)} 字背景资料'
                                }
                            })
                        
                        elif node_name == 'planner' and state.get('outline'):
                            # 大纲生成结果
                            outline = state.get('outline', {})
                            sections = outline.get('sections', [])
                            task_manager.send_event(task_id, 'result', {
                                'type': 'outline_complete',
                                'data': {
                                    'title': outline.get('title', ''),
                                    'sections_count': len(sections),
                                    'sections': [s.get('title', '') for s in sections],
                                    'message': f'大纲生成完成: {outline.get("title", "")} ({len(sections)} 章节)'
                                }
                            })
                        
                        elif node_name == 'writer' and state.get('sections'):
                            # 章节撰写进度
                            sections = state.get('sections', [])
                            new_count = len(sections)
                            if new_count > completed_sections:
                                # 有新章节完成
                                for i in range(completed_sections, new_count):
                                    section = sections[i]
                                    task_manager.send_event(task_id, 'result', {
                                        'type': 'section_complete',
                                        'data': {
                                            'section_index': i + 1,
                                            'title': section.get('title', ''),
                                            'content_length': len(section.get('content', '')),
                                            'message': f'章节 {i + 1} 撰写完成: {section.get("title", "")}'
                                        }
                                    })
                                completed_sections = new_count
                        
                        elif node_name == 'check_knowledge':
                            # 知识空白检查结果
                            gaps = state.get('knowledge_gaps', [])
                            search_count = state.get('search_count', 0)
                            max_search_count = state.get('max_search_count', 5)
                            task_manager.send_event(task_id, 'result', {
                                'type': 'check_knowledge_complete',
                                'data': {
                                    'gaps_count': len(gaps),
                                    'gaps': [g.get('description', '') for g in gaps[:3]],
                                    'search_count': search_count,
                                    'max_search_count': max_search_count,
                                    'message': f'知识检查完成: 发现 {len(gaps)} 个空白点 (搜索 {search_count}/{max_search_count})'
                                }
                            })
                        
                        elif node_name == 'refine_search':
                            # 细化搜索结果
                            search_count = state.get('search_count', 0)
                            max_search_count = state.get('max_search_count', 5)
                            search_history = state.get('search_history', [])
                            latest_search = search_history[-1] if search_history else {}
                            task_manager.send_event(task_id, 'result', {
                                'type': 'refine_search_complete',
                                'data': {
                                    'round': search_count,
                                    'max_rounds': max_search_count,
                                    'queries': latest_search.get('queries', []),
                                    'results_count': latest_search.get('results_count', 0),
                                    'message': f'第 {search_count} 轮搜索完成: 获取 {latest_search.get("results_count", 0)} 条结果'
                                }
                            })
                        
                        elif node_name == 'enhance_with_knowledge':
                            # 知识增强结果
                            accumulated_knowledge = state.get('accumulated_knowledge', '')
                            task_manager.send_event(task_id, 'result', {
                                'type': 'enhance_knowledge_complete',
                                'data': {
                                    'knowledge_length': len(accumulated_knowledge),
                                    'message': f'内容增强完成: 累积知识 {len(accumulated_knowledge)} 字'
                                }
                            })
                        
                        elif node_name == 'questioner':
                            # 追问检查结果
                            needs_deepen = state.get('needs_deepen', False)
                            task_manager.send_event(task_id, 'result', {
                                'type': 'questioner_complete',
                                'data': {
                                    'needs_deepen': needs_deepen,
                                    'message': '内容需要深化' if needs_deepen else '内容深度检查通过'
                                }
                            })
                        
                        elif node_name == 'coder' and state.get('code_blocks'):
                            # 代码生成结果
                            code_blocks = state.get('code_blocks', [])
                            task_manager.send_event(task_id, 'result', {
                                'type': 'coder_complete',
                                'data': {
                                    'code_blocks_count': len(code_blocks),
                                    'message': f'代码示例生成完成: {len(code_blocks)} 个代码块'
                                }
                            })
                        
                        elif node_name == 'artist' and state.get('images'):
                            # 配图生成结果
                            images = state.get('images', [])
                            task_manager.send_event(task_id, 'result', {
                                'type': 'artist_complete',
                                'data': {
                                    'images_count': len(images),
                                    'message': f'配图描述生成完成: {len(images)} 张'
                                }
                            })
                        
                        elif node_name == 'reviewer':
                            # 审核结果
                            review_score = state.get('review_score', 0)
                            review_passed = state.get('review_passed', False)
                            task_manager.send_event(task_id, 'result', {
                                'type': 'reviewer_complete',
                                'data': {
                                    'score': review_score,
                                    'passed': review_passed,
                                    'message': f'质量审核完成: {review_score} 分 {"✅ 通过" if review_passed else "❌ 需修订"}'
                                }
                            })
                        
                        elif node_name == 'assembler':
                            # 组装完成
                            markdown = state.get('final_markdown', '')
                            task_manager.send_event(task_id, 'result', {
                                'type': 'assembler_complete',
                                'data': {
                                    'markdown_length': len(markdown),
                                    'message': f'文档组装完成: {len(markdown)} 字'
                                }
                            })
            
            # 获取最终状态
            final_state = self.generator.app.get_state(config).values
            
            # 生成封面架构图（基于全文内容）
            outline = final_state.get('outline', {})
            markdown_content = final_state.get('final_markdown', '')
            # 从 final_state 获取图片风格参数
            image_style = final_state.get('image_style', '')
            cover_image_result = self._generate_cover_image(
                title=outline.get('title', topic),
                topic=topic,
                full_content=markdown_content,
                task_manager=task_manager,
                task_id=task_id,
                image_style=image_style
            )
            # 解构返回值：(外网URL, 本地路径, 文章摘要)
            cover_image_url = cover_image_result[0] if cover_image_result else None
            cover_image_path = cover_image_result[1] if cover_image_result else None
            article_summary = cover_image_result[2] if cover_image_result and len(cover_image_result) > 2 else None
            
            # 自动保存 Markdown 到文件（包含封面图）
            markdown_content = final_state.get('final_markdown', '')
            saved_path = None
            
            # 如果有封面图，在 Markdown 中插入封面图
            markdown_with_cover = markdown_content
            if cover_image_path and markdown_content:
                cover_filename = os.path.basename(cover_image_path)
                title = outline.get('title', topic)
                cover_section = f"\n![{title} - 架构图](./images/{cover_filename})\n\n---\n\n"
                # 在第一个 ## 之前插入封面图
                lines = markdown_content.split('\n')
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('## ') and i > 0:
                        insert_idx = i
                        break
                if insert_idx > 0:
                    lines.insert(insert_idx, cover_section)
                    markdown_with_cover = '\n'.join(lines)
                else:
                    markdown_with_cover = cover_section + markdown_content
            
            if markdown_content:
                saved_path = self._save_markdown(
                    task_id=task_id,
                    markdown=markdown_content,
                    outline=outline,
                    cover_image_path=cover_image_path
                )
            
            # 生成封面动画（如果用户选择了该选项且功能已启用）
            cover_video_path = None
            cover_video_enabled = os.environ.get('COVER_VIDEO_ENABLED', 'true').lower() == 'true'
            if generate_cover_video and cover_image_url and cover_video_enabled:
                cover_video_path = self._generate_cover_video(
                    history_id=task_id,
                    cover_image_url=cover_image_url,
                    task_manager=task_manager,
                    task_id=task_id
                )
            
            # 保存历史记录（使用包含封面图的 markdown）
            try:
                from services.database_service import get_db_service
                import json
                db_service = get_db_service()
                db_service.save_history(
                    history_id=task_id,
                    topic=topic,
                    article_type=article_type,
                    target_length=target_length,
                    markdown_content=markdown_with_cover,
                    outline=json.dumps(final_state.get('outline', {}), ensure_ascii=False),
                    sections_count=len(final_state.get('sections', [])),
                    code_blocks_count=len(final_state.get('code_blocks', [])),
                    images_count=len(final_state.get('images', [])),
                    review_score=final_state.get('review_score', 0),
                    cover_image=cover_image_path,
                    cover_video=cover_video_path,
                    target_sections_count=article_config.get('sections_count'),
                    target_images_count=article_config.get('images_count'),
                    target_code_blocks_count=article_config.get('code_blocks_count'),
                    target_word_count=article_config.get('target_word_count')
                )
                logger.info(f"历史记录已保存: {task_id}")
                
                # 保存博客摘要（复用封面图生成时的摘要，避免重复调用 LLM）
                try:
                    summary_to_save = article_summary
                    # 如果没有摘要（封面图生成失败或跳过），则单独生成
                    if not summary_to_save:
                        summary_to_save = extract_article_summary(
                            llm_client=self.generator.llm,
                            title=topic,
                            content=markdown_with_cover,
                            max_length=500
                        )
                    
                    if summary_to_save:
                        # 截取前 500 字作为摘要
                        summary_to_save = summary_to_save[:500]
                        db_service.update_history_summary(task_id, summary_to_save)
                        logger.info(f"博客摘要已保存: {task_id}")
                except Exception as e:
                    logger.warning(f"保存博客摘要失败: {e}")
                    
            except Exception as e:
                logger.warning(f"保存历史记录失败: {e}")
            
            # 发送完成事件（使用包含封面图的 markdown）
            if task_manager:
                task_manager.send_event(task_id, 'complete', {
                    'success': True,
                    'markdown': markdown_with_cover,
                    'outline': final_state.get('outline', {}),
                    'sections_count': len(final_state.get('sections', [])),
                    'images_count': len(final_state.get('images', [])),
                    'code_blocks_count': len(final_state.get('code_blocks', [])),
                    'review_score': final_state.get('review_score', 0),
                    'saved_path': saved_path,
                    'cover_video': cover_video_path
                })
            
            logger.info(f"博客生成完成: {task_id}, 保存到: {saved_path}")
            
        except Exception as e:
            logger.error(f"博客生成失败 [{task_id}]: {e}", exc_info=True)
            if task_manager:
                task_manager.send_event(task_id, 'error', {
                    'message': str(e),
                    'recoverable': False
                })
        finally:
            # 清理日志处理器
            if sse_handler:
                for logger_name in [
                    'services.blog_generator.generator',
                    'services.blog_generator.agents.researcher',
                    'services.blog_generator.agents.planner',
                    'services.blog_generator.agents.writer',
                    'services.blog_generator.agents.questioner',
                    'services.blog_generator.agents.coder',
                    'services.blog_generator.agents.artist',
                    'services.blog_generator.agents.reviewer',
                    'services.blog_generator.agents.assembler',
                    'services.blog_generator.services.search_service',
                ]:
                    logging.getLogger(logger_name).removeHandler(sse_handler)
    
    def _generate_cover_image(
        self,
        title: str,
        topic: str,
        full_content: str = "",
        task_manager=None,
        task_id: str = None,
        image_style: str = ""
    ) -> Optional[tuple]:
        """
        生成封面架构图
        
        Args:
            title: 文章标题
            topic: 技术主题
            full_content: 全文 Markdown 内容
            task_manager: 任务管理器
            task_id: 任务 ID
            image_style: 图片风格 ID（可选）
            
        Returns:
            (外网URL, 本地路径, 文章摘要) 元组，或 None
        """
        image_service = get_image_service()
        if not image_service or not image_service.is_available():
            logger.warning("图片生成服务不可用，跳过封面图生成")
            return None
        
        try:
            # Step 1: 调用 LLM 提炼全文摘要
            if task_manager and task_id:
                task_manager.send_event(task_id, 'log', {
                    'level': 'INFO',
                    'logger': 'blog_service',
                    'message': f'正在提炼文章摘要...'
                })
            
            article_summary = extract_article_summary(
                llm_client=self.generator.llm,
                title=title,
                content=full_content,
                max_length=None  # 封面图生成不限制长度
            )
            if not article_summary:
                article_summary = f"标题：{title}\n主题：{topic}"
            
            # Step 2: 生成封面图
            if task_manager and task_id:
                task_manager.send_event(task_id, 'log', {
                    'level': 'INFO',
                    'logger': 'blog_service',
                    'message': f'正在生成封面架构图...'
                })
            
            # 构建封面图 Prompt
            if image_style:
                # 使用风格管理器渲染 Prompt
                from services.image_styles import get_style_manager
                style_manager = get_style_manager()
                cover_prompt = style_manager.render_prompt(image_style, article_summary)
                logger.info(f"开始生成【封面图】({image_style}): {title}")
            else:
                # 兼容旧逻辑：使用原有模板
                from .prompts.prompt_manager import get_prompt_manager
                pm = get_prompt_manager()
                cover_prompt = pm.render_cover_image_prompt(article_summary=article_summary)
                logger.info(f"开始生成【封面图】: {title}")
            
            # 调用图片生成服务
            result = image_service.generate(
                prompt=cover_prompt,
                aspect_ratio=AspectRatio.LANDSCAPE_16_9,
                image_size=ImageSize.SIZE_2K,
                download=True
            )
            
            if result and result.local_path:
                logger.info(f"封面图生成成功: {result.local_path}")
                if task_manager and task_id:
                    task_manager.send_event(task_id, 'log', {
                        'level': 'INFO',
                        'logger': 'blog_service',
                        'message': f'封面架构图生成完成'
                    })
                # 返回 (外网URL, 本地路径, 文章摘要) 元组
                return (result.url, result.local_path, article_summary)
            else:
                logger.warning("封面图生成失败，未获取到图片路径")
                # 即使封面图生成失败，也返回摘要
                return (None, None, article_summary)
                
        except Exception as e:
            logger.error(f"封面图生成失败: {e}")
            return None
    
    def _generate_cover_video(
        self,
        history_id: str,
        cover_image_url: str,
        task_manager=None,
        task_id: str = None
    ) -> Optional[str]:
        """
        生成封面动画视频
        
        Args:
            history_id: 历史记录 ID
            cover_image_url: 封面图外网 URL（直接使用图片生成服务返回的 URL）
            task_manager: 任务管理器
            task_id: 任务 ID
            
        Returns:
            视频访问 URL 或 None
        """
        try:
            from services.video_service import get_video_service
            import os
            
            # 发送进度事件
            if task_manager and task_id:
                task_manager.send_event(task_id, 'progress', {
                    'stage': 'video',
                    'progress': 96,
                    'message': '正在生成封面动画...'
                })
                task_manager.send_event(task_id, 'log', {
                    'level': 'INFO',
                    'logger': 'blog_service',
                    'message': '开始生成封面动画视频...'
                })
            
            # 检查视频服务
            video_service = get_video_service()
            if not video_service or not video_service.is_available():
                logger.warning("视频生成服务不可用，跳过封面动画生成")
                return None
            
            # 直接使用图片生成服务返回的外网 URL
            logger.info(f"使用封面图 URL: {cover_image_url}")
            
            if task_manager and task_id:
                task_manager.send_event(task_id, 'log', {
                    'level': 'INFO',
                    'logger': 'blog_service',
                    'message': '开始生成动画视频...'
                })
            
            # 定义进度回调
            def progress_callback(progress, status):
                if task_manager and task_id:
                    task_manager.send_event(task_id, 'log', {
                        'level': 'INFO',
                        'logger': 'blog_service',
                        'message': f'视频生成进度: {progress}%'
                    })
            
            # 调用视频生成服务
            result = video_service.generate_from_image(
                image_url=cover_image_url,
                progress_callback=progress_callback
            )
            
            if not result:
                logger.warning("视频生成失败")
                return None
            
            # 构建视频访问 URL
            video_filename = os.path.basename(result.local_path) if result.local_path else None
            video_access_url = f"/outputs/videos/{video_filename}" if video_filename else result.url
            
            logger.info(f"封面动画生成成功: {video_access_url}")
            
            if task_manager and task_id:
                task_manager.send_event(task_id, 'log', {
                    'level': 'INFO',
                    'logger': 'blog_service',
                    'message': '封面动画生成完成'
                })
            
            return video_access_url
            
        except Exception as e:
            logger.error(f"封面动画生成失败: {e}", exc_info=True)
            return None
    
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
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
            
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
    
    def chat(self, messages, response_format=None):
        """
        调用 LLM 进行对话
        
        Args:
            messages: 消息列表
            response_format: 响应格式 (可选)，如 {"type": "json_object"}
            
        Returns:
            LLM 响应文本
        """
        # 直接调用 LLMService 的 chat 方法，传递 response_format
        result = self.llm_service.chat(messages, response_format=response_format)
        
        if result:
            return result
        else:
            raise Exception('LLM 调用失败')
    
    def chat_stream(self, messages, on_chunk=None):
        """
        流式调用 LLM 进行对话
        
        Args:
            messages: 消息列表
            on_chunk: 每收到一个 chunk 时的回调函数 (delta, accumulated)
            
        Returns:
            完整的 LLM 响应文本
        """
        if hasattr(self.llm_service, 'chat_stream'):
            result = self.llm_service.chat_stream(messages, on_chunk=on_chunk)
            if result:
                return result
            else:
                raise Exception('LLM 流式调用失败')
        else:
            # 降级为普通调用
            return self.chat(messages)


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
    from services.blog_generator.prompts.prompt_manager import get_prompt_manager
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
