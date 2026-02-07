"""
长文博客生成器 - LangGraph 工作流主入口
"""

import logging
from typing import Dict, Any, Optional, Literal, Callable

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .schemas.state import SharedState, create_initial_state
from .agents.researcher import ResearcherAgent
from .agents.planner import PlannerAgent
from .agents.writer import WriterAgent
from .agents.coder import CoderAgent
from .agents.artist import ArtistAgent
from .agents.questioner import QuestionerAgent
from .agents.reviewer import ReviewerAgent
from .agents.assembler import AssemblerAgent
from .agents.search_coordinator import SearchCoordinator

logger = logging.getLogger(__name__)


def _get_content_word_count(state: Dict[str, Any]) -> int:
    """计算当前 state 中所有章节内容的总字数"""
    sections = state.get('sections', [])
    total = 0
    for section in sections:
        content = section.get('content', '')
        if content:
            total += len(content)
    return total


def _log_word_count_diff(agent_name: str, before: int, after: int):
    """记录字数变化的 diff"""
    diff = after - before
    if diff >= 0:
        logger.info(f"📊 [{agent_name}] 字数变化: {before} → {after} (+{diff} 字)")
    else:
        logger.info(f"📊 [{agent_name}] 字数变化: {before} → {after} ({diff} 字)")


class BlogGenerator:
    """
    长文博客生成器
    
    基于 LangGraph 实现的 Multi-Agent 协同生成系统
    """
    
    def __init__(
        self,
        llm_client,
        search_service=None,
        knowledge_service=None,
        max_questioning_rounds: int = 2,
        max_revision_rounds: int = 3
    ):
        """
        初始化博客生成器
        
        Args:
            llm_client: LLM 客户端
            search_service: 搜索服务 (可选)
            knowledge_service: 知识服务 (可选，用于文档知识融合)
            max_questioning_rounds: 最大追问轮数
            max_revision_rounds: 最大修订轮数
        """
        self.llm = llm_client
        self.search_service = search_service
        self.knowledge_service = knowledge_service
        self.max_questioning_rounds = max_questioning_rounds
        self.max_revision_rounds = max_revision_rounds
        
        # 初始化各 Agent
        self.researcher = ResearcherAgent(llm_client, search_service, knowledge_service)
        self.planner = PlannerAgent(llm_client)
        self.writer = WriterAgent(llm_client)
        self.coder = CoderAgent(llm_client)
        self.artist = ArtistAgent(llm_client)
        self.questioner = QuestionerAgent(llm_client)
        self.reviewer = ReviewerAgent(llm_client)
        self.assembler = AssemblerAgent()
        self.search_coordinator = SearchCoordinator(llm_client, search_service)
        
        # 构建工作流
        self.workflow = self._build_workflow()
        self.app = None
    
    def _build_workflow(self) -> StateGraph:
        """
        构建 LangGraph 工作流
        
        Returns:
            StateGraph 实例
        """
        workflow = StateGraph(SharedState)
        
        # 添加节点
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("writer", self._writer_node)
        # 多轮搜索相关节点
        workflow.add_node("check_knowledge", self._check_knowledge_node)
        workflow.add_node("refine_search", self._refine_search_node)
        workflow.add_node("enhance_with_knowledge", self._enhance_with_knowledge_node)
        # 追问和审核节点
        workflow.add_node("questioner", self._questioner_node)
        workflow.add_node("deepen_content", self._deepen_content_node)
        workflow.add_node("coder_and_artist", self._coder_and_artist_node)  # 并行节点
        workflow.add_node("reviewer", self._reviewer_node)
        workflow.add_node("revision", self._revision_node)
        workflow.add_node("assembler", self._assembler_node)
        
        # 定义边
        workflow.add_edge(START, "researcher")
        workflow.add_edge("researcher", "planner")
        workflow.add_edge("planner", "writer")
        
        # Writer 后进入知识空白检查
        workflow.add_edge("writer", "check_knowledge")
        
        # 条件边：检查后决定是搜索还是继续到 Questioner
        workflow.add_conditional_edges(
            "check_knowledge",
            self._should_refine_search,
            {
                "search": "refine_search",
                "continue": "questioner"
            }
        )
        
        # 搜索后增强内容，然后回到知识检查
        workflow.add_edge("refine_search", "enhance_with_knowledge")
        workflow.add_edge("enhance_with_knowledge", "check_knowledge")
        
        # 条件边：追问后决定是深化还是继续
        workflow.add_conditional_edges(
            "questioner",
            self._should_deepen,
            {
                "deepen": "deepen_content",
                "continue": "coder_and_artist"  # 进入并行节点
            }
        )
        workflow.add_edge("deepen_content", "questioner")  # 深化后重新追问
        
        # Coder 和 Artist 并行执行（通过单个节点内部并行实现）
        workflow.add_edge("coder_and_artist", "reviewer")
        
        # 条件边：审核后决定是修订还是组装
        workflow.add_conditional_edges(
            "reviewer",
            self._should_revise,
            {
                "revision": "revision",
                "assemble": "assembler"
            }
        )
        workflow.add_edge("revision", "reviewer")  # 修订后重新审核
        workflow.add_edge("assembler", END)
        
        return workflow
    
    def _researcher_node(self, state: SharedState) -> SharedState:
        """素材收集节点"""
        logger.info("=== Step 1: 素材收集 ===")
        return self.researcher.run(state)
    
    def _planner_node(self, state: SharedState) -> SharedState:
        """大纲规划节点"""
        logger.info("=== Step 2: 大纲规划 ===")
        # 使用实例变量中的流式回调
        on_stream = getattr(self, '_outline_stream_callback', None)
        return self.planner.run(state, on_stream=on_stream)
    
    def _writer_node(self, state: SharedState) -> SharedState:
        """内容撰写节点"""
        logger.info("=== Step 3: 内容撰写 ===")
        before_count = _get_content_word_count(state)
        result = self.writer.run(state)
        after_count = _get_content_word_count(result)
        _log_word_count_diff("Writer", before_count, after_count)
        # 初始化累积知识（首次写作后）
        if not result.get('accumulated_knowledge'):
            result['accumulated_knowledge'] = result.get('background_knowledge', '')
        return result
    
    def _check_knowledge_node(self, state: SharedState) -> SharedState:
        """知识空白检查节点"""
        search_count = state.get('search_count', 0)
        max_count = state.get('max_search_count', 5)
        logger.info(f"=== Step 3.5: 知识空白检查 (搜索次数: {search_count}/{max_count}) ===")
        return self.search_coordinator.run(state)
    
    def _refine_search_node(self, state: SharedState) -> SharedState:
        """细化搜索节点"""
        search_count = state.get('search_count', 0) + 1
        max_count = state.get('max_search_count', 5)
        logger.info(f"=== Step 3.6: 细化搜索 (第 {search_count} 轮) ===")
        
        gaps = state.get('knowledge_gaps', [])
        result = self.search_coordinator.refine_search(gaps, state)
        
        if result.get('success'):
            logger.info(f"细化搜索完成: 获取 {len(result.get('results', []))} 条结果")
        else:
            logger.warning(f"细化搜索失败: {result.get('reason', '未知原因')}")
        
        return state
    
    def _enhance_with_knowledge_node(self, state: SharedState) -> SharedState:
        """基于新知识增强内容节点（并行）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os
        
        logger.info("=== Step 3.7: 知识增强 ===")
        
        sections = state.get('sections', [])
        gaps = state.get('knowledge_gaps', [])
        new_knowledge = state.get('accumulated_knowledge', '')
        
        if not gaps or not new_knowledge:
            logger.info("没有需要增强的内容")
            return state
        
        from .prompts import get_prompt_manager
        pm = get_prompt_manager()
        
        # 第一步：收集需要增强的任务
        tasks = []
        for section in sections:
            section_gaps = [g for g in gaps if not g.get('section_id') or g.get('section_id') == section.get('id')]
            
            if section_gaps:
                tasks.append({
                    'section': section,
                    'section_gaps': section_gaps,
                    'new_knowledge': new_knowledge
                })
        
        if not tasks:
            logger.info("没有需要增强的章节")
            state['knowledge_gaps'] = []
            return state
        
        max_workers = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))
        logger.info(f"开始知识增强: {len(tasks)} 个章节，使用 {min(max_workers, len(tasks))} 个并行线程")
        
        # 第二步：并行增强
        def enhance_task(task):
            """单个章节增强任务"""
            section = task['section']
            try:
                prompt = pm.render_writer_enhance_with_knowledge(
                    original_content=section.get('content', ''),
                    new_knowledge=task['new_knowledge'],
                    knowledge_gaps=task['section_gaps']
                )
                
                enhanced_content = self.writer.llm.chat(
                    messages=[{"role": "user", "content": prompt}]
                )
                return {
                    'success': True,
                    'section': section,
                    'enhanced_content': enhanced_content
                }
            except Exception as e:
                logger.error(f"章节增强失败 [{section.get('title', '')}]: {e}")
                return {
                    'success': False,
                    'section': section,
                    'error': str(e)
                }
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(enhance_task, task): task for task in tasks}
            
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    result['section']['content'] = result['enhanced_content']
                    logger.info(f"章节增强完成: {result['section'].get('title', '')}")
        
        enhanced_count = sum(1 for t in tasks if t['section'].get('content'))
        logger.info(f"知识增强完成: {enhanced_count} 个章节")
        
        # 清空已处理的知识空白
        state['knowledge_gaps'] = []
        
        return state
    
    
    
    def _questioner_node(self, state: SharedState) -> SharedState:
        """追问检查节点"""
        logger.info("=== Step 4: 追问检查 ===")
        return self.questioner.run(state)
    
    def _deepen_content_node(self, state: SharedState) -> SharedState:
        """内容深化节点"""
        logger.info("=== Step 4.1: 内容深化 ===")
        before_count = _get_content_word_count(state)
        state['questioning_count'] = state.get('questioning_count', 0) + 1
        
        # 统计需要深化的章节
        sections_to_deepen = [
            r for r in state.get('question_results', [])
            if not r.get('is_detailed_enough', True)
        ]
        total_to_deepen = len(sections_to_deepen)
        logger.info(f"开始深化 {total_to_deepen} 个章节")
        
        # 根据追问结果深化内容
        for idx, result in enumerate(sections_to_deepen, 1):
            section_id = result.get('section_id', '')
            vague_points = result.get('vague_points', [])
            
            # 找到对应章节
            for section in state.get('sections', []):
                if section.get('id') == section_id:
                    section_title = section.get('title', section_id)
                    original_length = len(section.get('content', ''))
                    
                    enhanced_content = self.writer.enhance_section(
                        original_content=section.get('content', ''),
                        vague_points=vague_points,
                        section_title=section_title,
                        progress_info=f"[{idx}/{total_to_deepen}]"
                    )
                    section['content'] = enhanced_content
                    
                    new_length = len(enhanced_content)
                    logger.info(f"章节深化完成: {section_title} (+{new_length - original_length} 字)")
                    break
        
        after_count = _get_content_word_count(state)
        _log_word_count_diff("内容深化", before_count, after_count)
        return state
    
    def _coder_and_artist_node(self, state: SharedState) -> SharedState:
        """代码和配图并行生成节点"""
        from concurrent.futures import ThreadPoolExecutor
        
        logger.info("=== Step 5: 代码和配图并行生成 ===")
        
        # 使用线程池并行执行 coder 和 artist
        # coder 修改: code_blocks, sections[x].code_ids
        # artist 修改: images, sections[x].image_ids
        # 两者不冲突，可以安全并行
        
        def run_coder():
            logger.info("→ 开始代码生成")
            return self.coder.run(state)
        
        def run_artist():
            logger.info("→ 开始配图生成（含补图检测）")
            return self.artist.run(state)
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            coder_future = executor.submit(run_coder)
            artist_future = executor.submit(run_artist)
            
            # 等待两者完成，并合并结果
            coder_result = coder_future.result()
            artist_result = artist_future.result()
            
            # 合并 artist 的结果到 state（特别是 section_images）
            if artist_result:
                if 'section_images' in artist_result:
                    state['section_images'] = artist_result['section_images']
                    logger.info(f"合并 section_images: {len(state['section_images'])} 张")
                if 'images' in artist_result:
                    state['images'] = artist_result['images']
        
        code_count = len(state.get('code_blocks', []))
        image_count = len(state.get('images', []))
        logger.info(f"=== 代码和配图并行生成完成: {code_count} 个代码块, {image_count} 张图片 ===")
        
        return state
    
    def _reviewer_node(self, state: SharedState) -> SharedState:
        """质量审核节点"""
        logger.info("=== Step 7: 质量审核 ===")
        return self.reviewer.run(state)
    
    def _revision_node(self, state: SharedState) -> SharedState:
        """修订节点"""
        logger.info("=== Step 7.1: 修订 ===")
        before_count = _get_content_word_count(state)
        state['revision_count'] = state.get('revision_count', 0) + 1
        
        # 根据审核问题修订内容
        review_issues = state.get('review_issues', [])
        total_issues = len(review_issues)
        target_length = state.get('target_length', 'medium')
        
        # Mini/Short 模式：按章节分组问题，使用 correct_section（只更正不扩展）
        if target_length in ('mini', 'short'):
            # 按章节分组问题
            section_issues = {}
            for issue in review_issues:
                section_id = issue.get('section_id', '')
                if section_id not in section_issues:
                    section_issues[section_id] = []
                section_issues[section_id].append({
                    'severity': issue.get('severity', 'medium'),
                    'description': issue.get('description', ''),
                    'affected_content': issue.get('affected_content', '')
                })
            
            # 对每个有问题的章节进行更正
            for idx, (section_id, issues) in enumerate(section_issues.items(), 1):
                for section in state.get('sections', []):
                    if section.get('id') == section_id:
                        section_title = section.get('title', section_id)
                        corrected_content = self.writer.correct_section(
                            original_content=section.get('content', ''),
                            issues=issues,
                            section_title=section_title,
                            progress_info=f"[{idx}/{len(section_issues)}]"
                        )
                        section['content'] = corrected_content
                        break
        else:
            # 其他模式：使用 enhance_section（可扩展内容）
            for idx, issue in enumerate(review_issues, 1):
                section_id = issue.get('section_id', '')
                suggestion = issue.get('suggestion', '')
                
                # 找到对应章节并修订
                for section in state.get('sections', []):
                    if section.get('id') == section_id:
                        section_title = section.get('title', section_id)
                        enhanced_content = self.writer.enhance_section(
                            original_content=section.get('content', ''),
                            vague_points=[{
                                'location': section_title,
                                'issue': issue.get('description', ''),
                                'question': suggestion,
                                'suggestion': '根据审核建议修改'
                            }],
                            section_title=section_title,
                            progress_info=f"[{idx}/{total_issues}]"
                        )
                        section['content'] = enhanced_content
                        break
        
        after_count = _get_content_word_count(state)
        _log_word_count_diff("修订", before_count, after_count)
        return state
    
    def _assembler_node(self, state: SharedState) -> SharedState:
        """文档组装节点"""
        logger.info("=== Step 8: 文档组装 ===")
        return self.assembler.run(state)
    
    def _should_deepen(self, state: SharedState) -> Literal["deepen", "continue"]:
        """判断是否需要深化内容"""
        if not state.get('all_sections_detailed', True):
            if state.get('questioning_count', 0) < self.max_questioning_rounds:
                return "deepen"
        return "continue"
    
    def _should_revise(self, state: SharedState) -> Literal["revision", "assemble"]:
        """判断是否需要修订"""
        target_length = state.get('target_length', 'medium')
        
        # Mini/Short 模式只处理 high 级别问题，且最多修订 1 轮
        if target_length in ('mini', 'short'):
            revision_count = state.get('revision_count', 0)
            # Mini 模式最多修订 1 轮
            if revision_count >= 1:
                logger.info(f"[{target_length}] 模式：已达到最大修订轮数 (1)，跳过修订")
                return "assemble"
            
            review_issues = state.get('review_issues', [])
            high_issues = [i for i in review_issues if i.get('severity') == 'high']
            if high_issues:
                logger.info(f"[{target_length}] 模式：只处理 {len(high_issues)} 个 high 级别问题")
                # 只保留 high 级别问题
                state['review_issues'] = high_issues
                return "revision"
            logger.info(f"[{target_length}] 模式：无 high 级别问题，跳过修订")
            return "assemble"
        
        if not state.get('review_approved', True):
            if state.get('revision_count', 0) < self.max_revision_rounds:
                return "revision"
        
        logger.info("审核通过或修订完成，进入组装")
        return "assemble"

    def _should_refine_search(self, state: SharedState) -> Literal["search", "continue"]:
        """判断是否需要细化搜索"""
        # Mini/Short 模式跳过知识增强，直接进入追问阶段
        target_length = state.get('target_length', 'medium')
        if target_length in ('mini', 'short'):
            logger.info(f"[{target_length}] 模式跳过知识增强")
            return "continue"
        
        gaps = state.get('knowledge_gaps', [])
        search_count = state.get('search_count', 0)
        max_count = state.get('max_search_count', 5)
        
        # 有知识空白且未达到搜索上限
        if gaps and search_count < max_count:
            # 检查是否有重要的空白（missing_data 或 vague_concept）
            important_gaps = [g for g in gaps if g.get('gap_type') in ['missing_data', 'vague_concept']]
            if important_gaps:
                logger.info(f"检测到 {len(important_gaps)} 个重要知识空白，触发细化搜索")
                return "search"
        
        logger.info("无需细化搜索，继续到追问阶段")
        return "continue"
    
    def compile(self, checkpointer=None):
        """
        编译工作流
        
        Args:
            checkpointer: 检查点存储 (可选)
        """
        if checkpointer is None:
            checkpointer = MemorySaver()
        
        self.app = self.workflow.compile(checkpointer=checkpointer)
        return self.app
    
    def generate(
        self,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        target_length: str = "medium",
        source_material: str = None,
        on_progress: Callable[[str, str], None] = None
    ) -> Dict[str, Any]:
        """
        生成博客
        
        Args:
            topic: 技术主题
            article_type: 文章类型
            target_audience: 目标受众
            target_length: 目标长度
            source_material: 参考资料
            on_progress: 进度回调
            
        Returns:
            生成结果
        """
        if self.app is None:
            self.compile()
        
        # 创建初始状态
        initial_state = create_initial_state(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material
        )
        
        logger.info(f"开始生成博客: {topic}")
        logger.info(f"  类型: {article_type}, 受众: {target_audience}, 长度: {target_length}")
        
        # 执行工作流
        config = {"configurable": {"thread_id": f"blog_{topic}"}}
        
        try:
            final_state = self.app.invoke(initial_state, config)
            
            logger.info("博客生成完成!")
            
            return {
                "success": True,
                "markdown": final_state.get('final_markdown', ''),
                "outline": final_state.get('outline', {}),
                "sections_count": len(final_state.get('sections', [])),
                "images_count": len(final_state.get('images', [])),
                "code_blocks_count": len(final_state.get('code_blocks', [])),
                "review_score": final_state.get('review_score', 0),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"博客生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "markdown": "",
                "error": str(e)
            }
    
    async def generate_stream(
        self,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        target_length: str = "medium",
        source_material: str = None
    ):
        """
        流式生成博客 (异步生成器)
        
        Args:
            topic: 技术主题
            article_type: 文章类型
            target_audience: 目标受众
            target_length: 目标长度
            source_material: 参考资料
            
        Yields:
            生成进度和中间结果
        """
        if self.app is None:
            self.compile()
        
        initial_state = create_initial_state(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material
        )
        
        config = {"configurable": {"thread_id": f"blog_{topic}"}}
        
        # 使用 stream 方法获取中间状态
        for event in self.app.stream(initial_state, config):
            for node_name, state in event.items():
                yield {
                    "stage": node_name,
                    "state": state
                }
