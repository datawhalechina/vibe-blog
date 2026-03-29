"""
Writer Agent - 内容撰写
"""

import json
import logging
import os
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..prompts import get_prompt_manager

# 从环境变量读取并行配置，默认为 3
MAX_WORKERS = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))

def _should_use_parallel(mode: str = None):
    """判断是否应该使用并行执行。mini 模式强制并行，其他模式受 TRACE_ENABLED 控制。"""
    if mode == 'mini':
        return True
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        return False
    return True

logger = logging.getLogger(__name__)

# Langfuse 追踪装饰器（只在 TRACE_ENABLED=true 时启用）
def _get_langfuse_client():
    """获取 Langfuse client，未启用时返回 None"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        try:
            from langfuse import get_client
            return get_client()
        except ImportError:
            pass
        except Exception:
            pass
    return None

def _get_observe_decorator():
    """获取 Langfuse observe 装饰器，未启用时返回空装饰器"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        try:
            from langfuse import observe
            return observe
        except ImportError:
            pass
    # 返回空装饰器
    def noop_decorator(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper if not args or not callable(args[0]) else func
    return noop_decorator

observe = _get_observe_decorator()
langfuse_client = _get_langfuse_client()


class WriterAgent:
    """
    内容撰写师 - 负责章节正文撰写
    """

    def __init__(self, llm_client):
        """
        初始化 Writer Agent

        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
        self.task_manager = None
        self.task_id = None

        # 37.13 写作模板体系（可选）
        self._prompt_composer = None
        self._template_data = None
        self._style_data = None
        try:
            from ..orchestrator.prompt_composer import PromptComposer
            from ..orchestrator.template_loader import TemplateLoader
            from ..orchestrator.style_loader import StyleLoader
            self._prompt_composer = PromptComposer()
            self._template_loader = TemplateLoader()
            self._style_loader = StyleLoader()
        except Exception:
            pass

    def _apply_template_and_style(self, base_prompt: str, agent_name: str, kwargs: dict) -> str:
        """应用写作模板和风格（37.13）"""
        if not self._prompt_composer:
            return base_prompt
        template_name = kwargs.get('template')
        style_name = kwargs.get('style')
        if not template_name and not style_name:
            return base_prompt
        template = self._template_loader.get(template_name) if template_name else None
        style = self._style_loader.get(style_name) if style_name else None
        if not template and not style:
            return base_prompt
        return self._prompt_composer.compose(
            agent_name=agent_name,
            base_prompt=base_prompt,
            template=template,
            style=style,
        )
    
    @observe(name="writer.write_section", as_type="generation")
    def write_section(
        self,
        section_outline: Dict[str, Any],
        previous_section_summary: str = "",
        next_section_preview: str = "",
        background_knowledge: str = "",
        audience_adaptation: str = "technical-beginner",
        search_results: List[Dict[str, Any]] = None,
        verbatim_data: List[Dict[str, Any]] = None,
        learning_objectives: List[Dict[str, Any]] = None,
        narrative_mode: str = "",
        narrative_flow: Dict[str, Any] = None,
        distilled_sources: List[Dict[str, Any]] = None,
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> Dict[str, Any]:
        """
        撰写单个章节
        
        Args:
            section_outline: 章节大纲
            previous_section_summary: 前一章节摘要
            next_section_preview: 后续章节预告
            background_knowledge: 背景知识
            audience_adaptation: 受众适配类型
            search_results: 原始搜索结果（用于准确引用）
            verbatim_data: 需要原样保留的数据
            learning_objectives: 学习目标列表（用于约束内容）
            narrative_mode: 叙事模式（如 what-why-how, tutorial, catalog）
            narrative_flow: 叙事流（reader_start, reader_end, logic_chain）
            
        Returns:
            章节内容
        """
        # Enrich assigned_materials with actual source data
        # 优先使用 distilled_sources（LLM 提炼的高质量摘要），回退到 search_results 短 snippet
        assigned_materials = []
        assigned_indices = set()
        raw_materials = section_outline.get('assigned_materials', [])
        distilled = distilled_sources or []
        for mat in raw_materials:
            source_idx = mat.get('source_index', 0)
            if source_idx > 0:
                assigned_indices.add(source_idx)
            enriched = dict(mat)
            # 优先从 distilled_sources 获取丰富的 core_insight
            distilled_match = None
            if distilled and search_results and 0 < source_idx <= len(search_results):
                source_url = search_results[source_idx - 1].get('url', '')
                source_title = search_results[source_idx - 1].get('title', '')
                for ds in distilled:
                    if ds.get('url') == source_url or ds.get('title') == source_title:
                        distilled_match = ds
                        break
            if distilled_match:
                enriched['title'] = distilled_match.get('title', '')
                enriched['url'] = distilled_match.get('url', '')
                enriched['core_insight'] = distilled_match.get('core_insight', '')
            elif search_results and 0 < source_idx <= len(search_results):
                source = search_results[source_idx - 1]
                enriched['title'] = source.get('title', '')
                enriched['url'] = source.get('url', source.get('source', ''))
                enriched['core_insight'] = source.get('content', '')[:300]
            assigned_materials.append(enriched)

        # 按 assigned_materials 过滤搜索结果，只传本章需要的素材
        # 使用 distilled_sources 替代原始短 snippet（如果可用）
        if assigned_indices and search_results:
            filtered_results = []
            for i, sr in enumerate(search_results, 1):
                if i not in assigned_indices:
                    continue
                # 尝试用 distilled 版本替换
                ds_match = None
                for ds in distilled:
                    if ds.get('url') == sr.get('url') or ds.get('title') == sr.get('title'):
                        ds_match = ds
                        break
                if ds_match:
                    filtered_results.append({
                        'title': ds_match.get('title', sr.get('title', '')),
                        'url': ds_match.get('url', sr.get('url', '')),
                        'content': ds_match.get('core_insight', sr.get('content', '')),
                    })
                else:
                    filtered_results.append(sr)
        else:
            filtered_results = search_results or []

        pm = get_prompt_manager()
        prompt = pm.render_writer(
            section_outline=section_outline,
            previous_section_summary=previous_section_summary,
            next_section_preview=next_section_preview,
            background_knowledge=background_knowledge,
            audience_adaptation=audience_adaptation,
            search_results=filtered_results,
            verbatim_data=verbatim_data or [],
            learning_objectives=learning_objectives or [],
            narrative_mode=narrative_mode,
            narrative_flow=narrative_flow or {},
            assigned_materials=assigned_materials
        )

        # 37.13 写作模板 + 风格注入
        prompt = self._apply_template_and_style(prompt, "writer", kwargs)

        # 102.06: 写作方法论技能注入
        writing_skill_prompt = kwargs.get('_writing_skill_prompt', '')
        if writing_skill_prompt:
            prompt = writing_skill_prompt + "\n\n" + prompt

        # 41.10: 动态 Agent 角色注入
        persona_prompt = kwargs.get('_persona_prompt', '')
        if persona_prompt:
            prompt = persona_prompt + "\n\n" + prompt
        
        # 输出完整的 Writer Prompt 到日志（用于诊断）
        logger.info(f"[Writer] ========== 章节 Prompt ({len(prompt)} 字): {section_outline.get('title', 'Unknown')} ==========")
        logger.debug(prompt)  # 完整 Prompt 仍用 debug 级别
        logger.info(f"[Writer] ========== Prompt 结束 ==========")
        
        try:
            # 流式写作回调：当 task_manager 存在且 LLM 支持 chat_stream 时
            has_stream = hasattr(self.llm, 'chat_stream') and self.task_manager and self.task_id
            if has_stream:
                section_title = section_outline.get('title', '')
                accumulated = ""
                import time as _time
                from services.llm_service import _strip_thinking
                _last_send = [0.0]  # 节流：最少间隔 100ms

                def on_writing_chunk(delta, acc):
                    nonlocal accumulated
                    accumulated = acc
                    # 清理 Gemini <think> 标签，只发送正文内容
                    cleaned = _strip_thinking(acc)
                    if not cleaned:
                        return  # 思考文本还没结束，不发送
                    now = _time.time()
                    if now - _last_send[0] < 0.1:
                        return  # 节流，跳过
                    _last_send[0] = now
                    self.task_manager.send_event(self.task_id, 'writing_chunk', {
                        'section_title': section_title,
                        'delta': delta,
                        'accumulated': cleaned,
                    })

                response = self.llm.chat_stream(
                    messages=[{"role": "user", "content": prompt}],
                    on_chunk=on_writing_chunk,
                    caller="writer",
                )
            else:
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    caller="writer",
                )

            return {
                "id": section_outline.get('id', ''),
                "title": section_outline.get('title', ''),
                "content": response,
                "image_ids": [],
                "code_ids": []
            }
            
        except Exception as e:
            logger.error(f"章节撰写失败 [{section_outline.get('title', '')}]: {e}")
            raise
    
    @observe(name="writer.enhance_section", as_type="generation")
    def enhance_section(
        self,
        original_content: str,
        vague_points: List[Dict[str, Any]],
        section_title: str = "",
        progress_info: str = "",
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> str:
        """
        根据追问深化章节内容
        
        Args:
            original_content: 原始内容
            vague_points: 模糊点列表
            section_title: 章节标题
            progress_info: 进度信息 (如 "[1/3]")
            
        Returns:
            增强后的内容
        """
        if not vague_points:
            return original_content
        
        display_title = section_title if section_title else "(未知章节)"
        display_progress = progress_info if progress_info else ""
        logger.info(f"正在深化章节 {display_progress} {display_title}")
        
        pm = get_prompt_manager()
        prompt = pm.render_writer_enhance(
            original_content=original_content,
            vague_points=vague_points
        )
        
        # 输出深化 Prompt 信息
        logger.info(f"[Writer] ========== 深化 Prompt ({len(prompt)} 字): {display_title} ==========")
        logger.debug(prompt)
        logger.info(f"[Writer] ========== Prompt 结束 ==========")
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                caller="writer",
            )
            return response
            
        except Exception as e:
            logger.error(f"章节深化失败: {e}")
            return original_content
    
    @observe(name="writer.correct_section", as_type="generation")
    def correct_section(
        self,
        original_content: str,
        issues: List[Dict[str, Any]],
        section_title: str = "",
        progress_info: str = "",
        **kwargs  # 接收 langfuse_parent_trace_id 等参数
    ) -> str:
        """
        更正章节内容（Mini/Short 模式专用）
        只删除/替换错误，不扩展内容
        
        Args:
            original_content: 原始内容
            issues: 审核问题列表，每个包含 severity, description, affected_content
            section_title: 章节标题
            progress_info: 进度信息 (如 "[1/3]")
            
        Returns:
            更正后的内容（字数 ≤ 原文）
        """
        if not issues:
            return original_content
        
        display_title = section_title if section_title else "(未知章节)"
        display_progress = progress_info if progress_info else ""
        logger.info(f"正在更正章节 {display_progress} {display_title} ({len(issues)} 个问题)")
        
        pm = get_prompt_manager()
        prompt = pm.render_writer_correct(
            section_title=section_title,
            original_content=original_content,
            issues=issues
        )
        
        # 输出更正 Prompt 信息
        original_word_count = len(original_content)
        logger.info(f"[Writer] ========== 更正 Prompt ({len(prompt)} 字): {display_title} ==========")
        logger.debug(prompt)
        logger.info(f"[Writer] ========== Prompt 结束 ==========")
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                caller="writer",
            )

            # 验证字数不超过原文
            corrected_word_count = len(response)
            if corrected_word_count > original_word_count * 1.1:  # 允许 10% 误差
                logger.warning(f"更正后字数 ({corrected_word_count}) 超过原文 ({original_word_count})，保留原文")
                return original_content
            
            logger.info(f"更正完成: {original_word_count} → {corrected_word_count} 字")
            return response
            
        except Exception as e:
            logger.error(f"章节更正失败: {e}")
            return original_content

    @observe(name="writer.improve_section", as_type="generation")
    def improve_section(
        self,
        original_content: str,
        critique: Dict[str, Any],
        section_title: str = "",
        **kwargs
    ) -> str:
        """
        基于结构化批评精准修改段落（Generator-Critic Loop 的 Generator 角色）

        Args:
            original_content: 原始章节内容
            critique: 评估结果，包含 scores/specific_issues/improvement_suggestions
            section_title: 章节标题

        Returns:
            修改后的章节内容
        """
        issues = critique.get("specific_issues", [])
        suggestions = critique.get("improvement_suggestions", [])
        if not issues and not suggestions:
            return original_content

        logger.info(
            f"[Writer] 精准修改章节 [{section_title}]: "
            f"{len(issues)} 个问题, {len(suggestions)} 条建议"
        )

        pm = get_prompt_manager()
        prompt = pm.render_writer_improve(
            original_content=original_content,
            scores=critique.get("scores", {}),
            specific_issues=issues,
            improvement_suggestions=suggestions,
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                caller="writer",
            )
            if response and response.strip():
                logger.info(
                    f"精准修改完成: {len(original_content)} → {len(response)} 字"
                )
                return response.strip()
            return original_content
        except Exception as e:
            logger.error(f"精准修改失败: {e}")
            return original_content

    @observe(name="writer.run")
    def run(self, state: Dict[str, Any], max_workers: int = None) -> Dict[str, Any]:
        """
        执行内容撰写（并行）
        
        Args:
            state: 共享状态
            max_workers: 最大并行数
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过内容撰写: {state.get('error')}")
            return state
        
        outline = state.get('outline')
        if outline is None:
            error_msg = "大纲为空，无法进行内容撰写"
            logger.error(error_msg)
            state['error'] = error_msg
            return state
        
        sections_outline = outline.get('sections', [])
        background_knowledge = state.get('background_knowledge', '')
        search_results = state.get('search_results', [])
        distilled_sources = state.get('distilled_sources', [])
        verbatim_data = state.get('verbatim_data', [])
        learning_objectives = state.get('learning_objectives', [])
        narrative_mode = outline.get('narrative_mode', '')
        narrative_flow = outline.get('narrative_flow', {})
        
        if not sections_outline:
            logger.warning("没有章节大纲，跳过内容撰写")
            state['sections'] = []
            return state
        
        # 第一步：收集所有章节撰写任务，预先分配顺序索引
        tasks = []
        for i, section_outline in enumerate(sections_outline):
            prev_summary = ""
            next_preview = ""
            
            if i > 0:
                prev_section = sections_outline[i - 1]
                prev_summary = f"上一章节《{prev_section.get('title', '')}》讨论了 {prev_section.get('key_concept', '')}"
            
            if i < len(sections_outline) - 1:
                next_section = sections_outline[i + 1]
                next_preview = f"下一章节《{next_section.get('title', '')}》将介绍 {next_section.get('key_concept', '')}"
            
            tasks.append({
                'order_idx': i,
                'section_outline': section_outline,
                'prev_summary': prev_summary,
                'next_preview': next_preview,
                'background_knowledge': background_knowledge if i == 0 else (background_knowledge[:100] + '...' if len(background_knowledge) > 100 else background_knowledge),
                'audience_adaptation': state.get('audience_adaptation', 'technical-beginner'),
                'search_results': [] if section_outline.get('assigned_materials') else search_results,
                'distilled_sources': distilled_sources,
                'verbatim_data': verbatim_data,
                'learning_objectives': learning_objectives,
                'narrative_mode': narrative_mode,
                'narrative_flow': narrative_flow,
                'template': state.get('writing_template'),  # 37.13
                'style': state.get('writing_style'),  # 37.13
                '_writing_skill_prompt': state.get('_writing_skill_prompt', ''),  # 102.06
                '_persona_prompt': state.get('_persona_prompt', ''),  # 41.10
            })
        
        # 使用环境变量配置或传入的参数
        if max_workers is None:
            max_workers = MAX_WORKERS
        
        target_length = state.get('target_length', '')
        use_parallel = _should_use_parallel(mode=target_length)
        if use_parallel and max_workers < 3:
            max_workers = 3  # mini 模式强制并行时，确保至少 3 个线程
        if use_parallel:
            logger.info(f"开始撰写内容: {len(tasks)} 个章节，使用 {min(max_workers, len(tasks))} 个并行线程")
        else:
            logger.info(f"开始撰写内容: {len(tasks)} 个章节，使用串行模式（追踪已启用）")
        
        # 第二步：撰写章节
        results = [None] * len(tasks)
        
        def write_single_task(task):
            """单个章节撰写任务"""
            try:
                section = self.write_section(
                    section_outline=task['section_outline'],
                    previous_section_summary=task['prev_summary'],
                    next_section_preview=task['next_preview'],
                    background_knowledge=task['background_knowledge'],
                    audience_adaptation=task.get('audience_adaptation', 'technical-beginner'),
                    search_results=task.get('search_results', []),
                    verbatim_data=task.get('verbatim_data', []),
                    learning_objectives=task.get('learning_objectives', []),
                    narrative_mode=task.get('narrative_mode', ''),
                    narrative_flow=task.get('narrative_flow', {}),
                    distilled_sources=task.get('distilled_sources', []),
                    template=task.get('template'),  # 37.13
                    style=task.get('style'),  # 37.13
                    _writing_skill_prompt=task.get('_writing_skill_prompt', ''),  # 102.06
                )
                return {
                    'success': True,
                    'order_idx': task['order_idx'],
                    'section': section
                }
            except Exception as e:
                logger.error(f"章节撰写失败 [{task['section_outline'].get('title', '')}]: {e}")
                return {
                    'success': False,
                    'order_idx': task['order_idx'],
                    'title': task['section_outline'].get('title', ''),
                    'error': str(e)
                }
        
        if use_parallel:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(write_single_task, task): task for task in tasks}
                
                for future in as_completed(futures):
                    result = future.result()
                    order_idx = result['order_idx']
                    results[order_idx] = result
                    
                    if result['success']:
                        logger.info(f"章节撰写完成: {result['section'].get('title', '')}")
        else:
            # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
            for task in tasks:
                try:
                    section = self.write_section(
                        section_outline=task['section_outline'],
                        previous_section_summary=task['prev_summary'],
                        next_section_preview=task['next_preview'],
                        background_knowledge=task['background_knowledge'],
                        audience_adaptation=task.get('audience_adaptation', 'technical-beginner'),
                        search_results=task.get('search_results', []),
                        verbatim_data=task.get('verbatim_data', []),
                        learning_objectives=task.get('learning_objectives', []),
                        narrative_mode=task.get('narrative_mode', ''),
                        narrative_flow=task.get('narrative_flow', {}),
                        distilled_sources=task.get('distilled_sources', []),
                        template=task.get('template'),  # 37.13
                        style=task.get('style'),  # 37.13
                    )
                    results[task['order_idx']] = {
                        'success': True,
                        'order_idx': task['order_idx'],
                        'section': section
                    }
                    logger.info(f"章节撰写完成: {section.get('title', '')}")
                except Exception as e:
                    logger.error(f"章节撰写失败 [{task['section_outline'].get('title', '')}]: {e}")
                    results[task['order_idx']] = {
                        'success': False,
                        'order_idx': task['order_idx'],
                        'title': task['section_outline'].get('title', ''),
                        'error': str(e)
                    }
        
        # 第三步：按原始顺序组装结果
        sections = []
        for result in results:
            if result and result['success']:
                sections.append(result['section'])
        
        state['sections'] = sections
        logger.info(f"内容撰写完成: {len(sections)} 个章节")
        
        return state
