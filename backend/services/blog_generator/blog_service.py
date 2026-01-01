"""
博客生成服务 - 封装 BlogGenerator，提供与 Banana Vibe Blog 集成的接口
"""

import logging
import threading
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from queue import Queue

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
    博客生成服务 - 与 Banana Vibe Blog 任务管理系统集成
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
        target_length: str = "medium",
        source_material: str = None,
        document_ids: list = None,
        document_knowledge: list = None,
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
            target_length: 目标长度
            source_material: 参考资料
            document_ids: 文档 ID 列表
            document_knowledge: 文档知识列表
            task_manager: 任务管理器
            app: Flask 应用实例
        """
        def run_in_thread():
            if app:
                with app.app_context():
                    self._run_generation(
                        task_id=task_id,
                        topic=topic,
                        article_type=article_type,
                        target_audience=target_audience,
                        target_length=target_length,
                        source_material=source_material,
                        document_ids=document_ids,
                        document_knowledge=document_knowledge,
                        task_manager=task_manager
                    )
            else:
                self._run_generation(
                    task_id=task_id,
                    topic=topic,
                    article_type=article_type,
                    target_audience=target_audience,
                    target_length=target_length,
                    source_material=source_material,
                    document_ids=document_ids,
                    document_knowledge=document_knowledge,
                    task_manager=task_manager
                )
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _run_generation(
        self,
        task_id: str,
        topic: str,
        article_type: str,
        target_audience: str,
        target_length: str,
        source_material: str,
        document_ids: list = None,
        document_knowledge: list = None,
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
            
            # 创建初始状态（支持文档知识）
            initial_state = create_initial_state(
                topic=topic,
                article_type=article_type,
                target_audience=target_audience,
                target_length=target_length,
                source_material=source_material,
                document_ids=document_ids or [],
                document_knowledge=document_knowledge or []
            )
            
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
                            task_manager.send_event(task_id, 'result', {
                                'type': 'researcher_complete',
                                'data': {
                                    'background_length': len(background),
                                    'key_concepts': key_concepts[:5] if key_concepts else [],
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
            cover_image_path = self._generate_cover_image(
                title=outline.get('title', topic),
                topic=topic,
                full_content=markdown_content,
                task_manager=task_manager,
                task_id=task_id
            )
            
            # 自动保存 Markdown 到文件（包含封面图）
            markdown_content = final_state.get('final_markdown', '')
            saved_path = None
            if markdown_content:
                saved_path = self._save_markdown(
                    task_id=task_id,
                    markdown=markdown_content,
                    outline=outline,
                    cover_image_path=cover_image_path
                )
            
            # 发送完成事件
            if task_manager:
                task_manager.send_event(task_id, 'complete', {
                    'success': True,
                    'markdown': markdown_content,
                    'outline': final_state.get('outline', {}),
                    'sections_count': len(final_state.get('sections', [])),
                    'images_count': len(final_state.get('images', [])),
                    'code_blocks_count': len(final_state.get('code_blocks', [])),
                    'review_score': final_state.get('review_score', 0),
                    'saved_path': saved_path
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
        task_id: str = None
    ) -> Optional[str]:
        """
        生成封面架构图
        
        Args:
            title: 文章标题
            topic: 技术主题
            full_content: 全文 Markdown 内容
            task_manager: 任务管理器
            task_id: 任务 ID
            
        Returns:
            图片本地路径
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
            
            article_summary = self._extract_article_summary(full_content, title, topic)
            
            # Step 2: 生成封面图
            if task_manager and task_id:
                task_manager.send_event(task_id, 'log', {
                    'level': 'INFO',
                    'logger': 'blog_service',
                    'message': f'正在生成封面架构图...'
                })
            
            # 构建封面图 Prompt（使用模板）
            from .prompts.prompt_manager import get_prompt_manager
            pm = get_prompt_manager()
            cover_prompt = pm.render_cover_image_prompt(article_summary=article_summary)
            
            # 调用图片生成服务
            logger.info(f"开始生成【封面图】: {title}")
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
                return result.local_path
            else:
                logger.warning("封面图生成失败，未获取到图片路径")
                return None
                
        except Exception as e:
            logger.error(f"封面图生成失败: {e}")
            return None
    
    def _extract_article_summary(
        self,
        full_content: str,
        title: str,
        topic: str
    ) -> str:
        """
        调用 LLM 提炼全文摘要，用于生成封面图
        
        Args:
            full_content: 全文 Markdown 内容
            title: 文章标题
            topic: 技术主题
            
        Returns:
            提炼后的摘要文本
        """
        if not full_content:
            return f"标题：{title}\n主题：{topic}"
        
        # 限制输入长度，避免超出 token 限制
        content_for_summary = full_content[:8000] if len(full_content) > 8000 else full_content
        
        summary_prompt = f"""请阅读以下技术博客文章，提炼出一份简洁的内容摘要，用于生成文章封面信息图。

要求：
1. 提取文章的核心主题和关键概念（3-5个）
2. 总结文章的主要章节和知识点
3. 识别文章中涉及的技术栈、工具或框架
4. 摘要控制在 1000 字以内
5. 使用与原文相同的语言

【文章标题】：{title}

【文章内容】：
{content_for_summary}

请直接输出摘要内容，不要添加额外的格式或标记："""

        try:
            # 使用 generator 的 LLM 客户端
            response = self.generator.llm.chat(
                messages=[{"role": "user", "content": summary_prompt}]
            )
            
            if response:
                logger.info(f"文章摘要提炼完成: {len(response)} 字")
                return f"标题：{title}\n\n{response}"
            else:
                logger.warning("摘要提炼失败，使用默认内容")
                return f"标题：{title}\n主题：{topic}"
                
        except Exception as e:
            logger.error(f"摘要提炼失败: {e}")
            return f"标题：{title}\n主题：{topic}"
    
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
            response_format: 响应格式 (可选)
            
        Returns:
            LLM 响应文本
        """
        # 直接调用 LLMService 的 chat 方法
        result = self.llm_service.chat(messages)
        
        if result:
            return result
        else:
            raise Exception('LLM 调用失败')


def get_blog_service() -> Optional[BlogService]:
    """获取博客生成服务实例"""
    return _blog_service
