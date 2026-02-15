"""
长文博客生成器 - LangGraph 工作流主入口
"""

import logging
import os
from typing import Dict, Any, Optional, Literal, Callable


def _should_use_parallel():
    """判断是否应该使用并行执行。当开启追踪时禁用并行，避免上下文丢失。"""
    if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
        return False
    return True

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from .schemas.state import SharedState, create_initial_state
from .style_profile import StyleProfile
from .agents.researcher import ResearcherAgent
from .agents.planner import PlannerAgent
from .agents.writer import WriterAgent
from .agents.coder import CoderAgent
from .agents.artist import ArtistAgent
from .agents.questioner import QuestionerAgent
from .agents.reviewer import ReviewerAgent
from .agents.assembler import AssemblerAgent
from .agents.search_coordinator import SearchCoordinator
from .agents.humanizer import HumanizerAgent
from utils.session_tracker import SessionTracker
from .agents.thread_checker import ThreadCheckerAgent
from .agents.voice_checker import VoiceCheckerAgent
from .agents.factcheck import FactCheckAgent
from .agents.summary_generator import SummaryGeneratorAgent

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
        max_revision_rounds: int = 3,
        style: StyleProfile = None
    ):
        """
        初始化博客生成器

        Args:
            llm_client: LLM 客户端
            search_service: 搜索服务 (可选)
            knowledge_service: 知识服务 (可选，用于文档知识融合)
            max_questioning_rounds: 最大追问轮数
            max_revision_rounds: 最大修订轮数
            style: 风格配置（可选，不传则从环境变量构建默认值）
        """
        self.llm = llm_client
        self.search_service = search_service
        self.knowledge_service = knowledge_service
        self.max_questioning_rounds = max_questioning_rounds
        self.style = style  # 延迟初始化：generate() 时根据 target_length 确定

        # max_revision_rounds 向后兼容：优先用 StyleProfile，否则用参数
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

        # 增强 Agent：环境变量作为全局开关（StyleProfile 作为运行时开关）
        self._env_humanizer = os.getenv('HUMANIZER_ENABLED', 'true').lower() == 'true'
        self._env_thread_check = os.getenv('THREAD_CHECK_ENABLED', 'true').lower() == 'true'
        self._env_voice_check = os.getenv('VOICE_CHECK_ENABLED', 'true').lower() == 'true'
        self._env_factcheck = os.getenv('FACTCHECK_ENABLED', 'true').lower() == 'true'
        self._env_text_cleanup = os.getenv('TEXT_CLEANUP_ENABLED', 'true').lower() == 'true'
        self._env_summary = os.getenv('SUMMARY_GENERATOR_ENABLED', 'true').lower() == 'true'

        # 初始化增强 Agent（只要环境变量没禁用就创建实例）
        self.humanizer = HumanizerAgent(llm_client) if self._env_humanizer else None
        self.thread_checker = ThreadCheckerAgent(llm_client) if self._env_thread_check else None
        self.voice_checker = VoiceCheckerAgent(llm_client) if self._env_voice_check else None
        self.factcheck = FactCheckAgent(llm_client) if self._env_factcheck else None

        # 业务级状态追踪（69.05）
        self.tracker = SessionTracker()
        self.summary_generator = SummaryGeneratorAgent(llm_client) if self._env_summary else None

        # 37.12 分层架构校验器（可选）
        self._layer_validator = None
        if os.environ.get('LAYER_VALIDATION_ENABLED', 'false').lower() == 'true':
            try:
                from .orchestrator.layer_definitions import BLOG_LAYERS, LayerValidator
                self._layer_validator = LayerValidator(BLOG_LAYERS)
                logger.info("🏗️ 分层架构校验已启用")
            except Exception as e:
                logger.warning(f"分层架构校验初始化失败: {e}")

        # 构建工作流
        self.workflow = self._build_workflow()
        self.app = None

    def _validate_layer(self, layer_name: str, state: Dict[str, Any]):
        """37.12 层间数据契约校验（仅日志警告，不阻断流程）"""
        if not self._layer_validator:
            return
        try:
            ok, missing = self._layer_validator.validate_inputs(layer_name, state)
            if not ok:
                logger.warning(f"🏗️ [{layer_name}] 层输入缺失: {missing}")
        except Exception as e:
            logger.debug(f"层校验异常: {e}")
    
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
        workflow.add_node("section_evaluate", self._section_evaluate_node)  # 段落评估
        workflow.add_node("section_improve", self._section_improve_node)  # 段落改进
        workflow.add_node("consistency_check", self._consistency_check_node)  # 一致性检查
        workflow.add_node("reviewer", self._reviewer_node)
        workflow.add_node("revision", self._revision_node)
        workflow.add_node("factcheck", self._factcheck_node)
        workflow.add_node("text_cleanup", self._text_cleanup_node)
        workflow.add_node("humanizer", self._humanizer_node)
        workflow.add_node("assembler", self._assembler_node)
        workflow.add_node("summary_generator", self._summary_generator_node)
        
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
                "continue": "section_evaluate"  # 进入段落评估
            }
        )
        workflow.add_edge("deepen_content", "questioner")  # 深化后重新追问

        # 段落评估 → 条件边：需要改进则进入改进节点，否则跳过
        workflow.add_conditional_edges(
            "section_evaluate",
            self._should_improve_sections,
            {
                "improve": "section_improve",
                "continue": "coder_and_artist",
            }
        )
        workflow.add_edge("section_improve", "section_evaluate")  # 改进后重新评估
        
        # Coder 和 Artist 并行执行（通过单个节点内部并行实现）
        workflow.add_edge("coder_and_artist", "consistency_check")
        workflow.add_edge("consistency_check", "reviewer")
        
        # 条件边：审核后决定是修订还是进入去 AI 味
        workflow.add_conditional_edges(
            "reviewer",
            self._should_revise,
            {
                "revision": "revision",
                "assemble": "factcheck"
            }
        )
        workflow.add_edge("revision", "reviewer")  # 修订后重新审核
        workflow.add_edge("factcheck", "text_cleanup")  # 事实核查后文本清理
        workflow.add_edge("text_cleanup", "humanizer")  # 文本清理后去 AI 味
        workflow.add_edge("humanizer", "assembler")  # 去 AI 味后组装
        workflow.add_edge("assembler", "summary_generator")
        workflow.add_edge("summary_generator", END)
        
        return workflow
    
    def _researcher_node(self, state: SharedState) -> SharedState:
        """素材收集节点"""
        if state.get('skip_researcher'):
            logger.info("=== Step 1: 素材收集（已跳过） ===")
            return state
        logger.info("=== Step 1: 素材收集 ===")
        self._validate_layer("research", state)
        return self.researcher.run(state)
    
    def _planner_node(self, state: SharedState) -> SharedState:
        """大纲规划节点"""
        logger.info("=== Step 2: 大纲规划 ===")
        self._validate_layer("structure", state)
        # 使用实例变量中的流式回调
        on_stream = getattr(self, '_outline_stream_callback', None)
        result = self.planner.run(state, on_stream=on_stream)

        # 交互式模式：使用 LangGraph 原生 interrupt 暂停图执行
        outline = result.get('outline') if isinstance(result, dict) else None
        if outline and getattr(self, '_interactive', False):
            sections = outline.get('sections', [])
            interrupt_data = {
                "type": "confirm_outline",
                "title": outline.get("title", ""),
                "sections": sections,
                "sections_titles": [s.get("title", "") for s in sections],
                "narrative_mode": outline.get("narrative_mode", ""),
                "narrative_flow": outline.get("narrative_flow", {}),
                "sections_narrative_roles": [s.get("narrative_role", "") for s in sections],
            }
            user_decision = interrupt(interrupt_data)

            # 处理用户决策
            if isinstance(user_decision, dict) and user_decision.get("action") == "edit":
                edited_outline = user_decision.get("outline", outline)
                logger.info(f"大纲已被用户修改: {edited_outline.get('title', '')}")
                result['outline'] = edited_outline
                result['sections'] = []  # 清空已有章节，重新写作
            else:
                logger.info("大纲已被用户确认")

        return result
    
    def _writer_node(self, state: SharedState) -> SharedState:
        """内容撰写节点"""
        logger.info("=== Step 3: 内容撰写 ===")
        self._validate_layer("content", state)
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
        """内容深化节点（并行）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os
        
        logger.info("=== Step 4.1: 内容深化 ===")
        before_count = _get_content_word_count(state)
        state['questioning_count'] = state.get('questioning_count', 0) + 1
        
        # 统计需要深化的章节
        sections_to_deepen = [
            r for r in state.get('question_results', [])
            if not r.get('is_detailed_enough', True)
        ]
        total_to_deepen = len(sections_to_deepen)
        
        if total_to_deepen == 0:
            logger.info("没有需要深化的章节")
            return state
        
        max_workers = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))
        use_parallel = _should_use_parallel()
        
        if use_parallel:
            logger.info(f"开始深化 {total_to_deepen} 个章节，使用 {min(max_workers, total_to_deepen)} 个并行线程")
        else:
            logger.info(f"开始深化 {total_to_deepen} 个章节，使用串行模式（追踪已启用）")
        
        # 准备任务列表
        tasks = []
        for idx, result in enumerate(sections_to_deepen, 1):
            section_id = result.get('section_id', '')
            vague_points = result.get('vague_points', [])
            
            # 找到对应章节
            for section in state.get('sections', []):
                if section.get('id') == section_id:
                    tasks.append({
                        'order_idx': idx - 1,
                        'section': section,
                        'section_id': section_id,
                        'vague_points': vague_points,
                        'progress_info': f"[{idx}/{total_to_deepen}]"
                    })
                    break
        
        # 执行深化
        def enhance_single_task(task):
            """单个章节深化任务"""
            try:
                section = task['section']
                section_title = section.get('title', task['section_id'])
                original_length = len(section.get('content', ''))
                
                enhanced_content = self.writer.enhance_section(
                    original_content=section.get('content', ''),
                    vague_points=task['vague_points'],
                    section_title=section_title,
                    progress_info=task['progress_info']
                )
                
                new_length = len(enhanced_content)
                logger.info(f"章节深化完成: {section_title} (+{new_length - original_length} 字)")
                
                return {
                    'success': True,
                    'section_id': task['section_id'],
                    'enhanced_content': enhanced_content
                }
            except Exception as e:
                logger.error(f"章节深化失败 [{task['section_id']}]: {e}")
                return {
                    'success': False,
                    'section_id': task['section_id'],
                    'enhanced_content': None
                }
        
        if use_parallel:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(enhance_single_task, task): task for task in tasks}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result['success']:
                        for section in state.get('sections', []):
                            if section.get('id') == result['section_id']:
                                section['content'] = result['enhanced_content']
                                break
        else:
            # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
            for task in tasks:
                try:
                    section = task['section']
                    section_title = section.get('title', task['section_id'])
                    original_length = len(section.get('content', ''))
                    
                    enhanced_content = self.writer.enhance_section(
                        original_content=section.get('content', ''),
                        vague_points=task['vague_points'],
                        section_title=section_title,
                        progress_info=task['progress_info']
                    )
                    
                    new_length = len(enhanced_content)
                    logger.info(f"章节深化完成: {section_title} (+{new_length - original_length} 字)")
                    
                    for s in state.get('sections', []):
                        if s.get('id') == task['section_id']:
                            s['content'] = enhanced_content
                            break
                except Exception as e:
                    logger.error(f"章节深化失败 [{task['section_id']}]: {e}")
        
        after_count = _get_content_word_count(state)
        _log_word_count_diff("内容深化", before_count, after_count)

        # 69.05: 记录深化迭代快照
        self.tracker.log_deepen_snapshot(
            round_num=state.get('questioning_count', 0),
            sections_deepened=total_to_deepen,
            chars_added=after_count - before_count,
        )

        return state

    # ========== 段落级 Generator-Critic Loop (#69.04) ==========

    def _section_evaluate_node(self, state: SharedState) -> SharedState:
        """段落多维度评估节点（Critic 角色）"""
        # 双开关：环境变量 + StyleProfile
        style = self._get_style(state)
        if not self._is_enabled("SECTION_EVAL_ENABLED", getattr(style, "enable_thread_check", True)):
            logger.info("段落评估已禁用，跳过")
            state["section_evaluations"] = []
            state["needs_section_improvement"] = False
            return state

        logger.info("=== Step 4.2: 段落多维度评估 ===")
        sections = state.get("sections", [])
        evaluations = []
        needs_improvement = False

        for i, section in enumerate(sections):
            prev_summary = sections[i - 1].get("title", "") if i > 0 else ""
            next_preview = sections[i + 1].get("title", "") if i < len(sections) - 1 else ""

            evaluation = self.questioner.evaluate_section(
                section_content=section.get("content", ""),
                section_title=section.get("title", ""),
                prev_summary=prev_summary,
                next_preview=next_preview,
            )
            evaluation["section_idx"] = i
            evaluations.append(evaluation)

            if evaluation["overall_quality"] < 7.0:
                needs_improvement = True
                logger.info(
                    f"  段落 [{section.get('title', '')}] 需改进: "
                    f"overall={evaluation['overall_quality']}"
                )

        state["section_evaluations"] = evaluations
        state["needs_section_improvement"] = needs_improvement

        avg_score = (
            sum(e["overall_quality"] for e in evaluations) / max(len(evaluations), 1)
        )
        logger.info(f"段落评估完成: 平均分 {avg_score:.1f}, 需改进={needs_improvement}")

        # 69.05: 记录段落评估分数
        for evaluation in evaluations:
            self.tracker.log_section_evaluation(
                section_title=sections[evaluation.get("section_idx", 0)].get("title", ""),
                scores=evaluation.get("scores", {}),
                overall=evaluation["overall_quality"],
            )

        return state

    def _should_improve_sections(self, state: SharedState) -> str:
        """判断是否需要段落级改进"""
        if not state.get("needs_section_improvement", False):
            return "continue"

        improve_count = state.get("section_improve_count", 0)
        if improve_count >= 2:
            logger.info("段落改进达到最大轮数(2)，跳过")
            return "continue"

        # 收敛检测：改进幅度 < 0.3 则停止
        evaluations = state.get("section_evaluations", [])
        curr_avg = (
            sum(e["overall_quality"] for e in evaluations) / max(len(evaluations), 1)
        )
        prev_avg = state.get("prev_section_avg_score", 0)
        if prev_avg > 0 and (curr_avg - prev_avg) < 0.3:
            logger.info(f"段落改进收敛 ({prev_avg:.1f} → {curr_avg:.1f})，跳过")
            return "continue"

        state["prev_section_avg_score"] = curr_avg
        return "improve"

    def _section_improve_node(self, state: SharedState) -> SharedState:
        """段落精准改进节点（Generator 角色）"""
        logger.info("=== Step 4.3: 段落精准改进 ===")
        evaluations = state.get("section_evaluations", [])
        sections = state.get("sections", [])
        improved_count = 0

        for evaluation in evaluations:
            idx = evaluation.get("section_idx", -1)
            if evaluation["overall_quality"] >= 7.0 or idx < 0 or idx >= len(sections):
                continue

            section = sections[idx]
            improved_content = self.writer.improve_section(
                original_content=section.get("content", ""),
                critique=evaluation,
                section_title=section.get("title", ""),
            )
            section["content"] = improved_content
            improved_count += 1

        state["section_improve_count"] = state.get("section_improve_count", 0) + 1
        logger.info(f"段落改进完成: 改进了 {improved_count} 个段落 (第 {state['section_improve_count']} 轮)")

        # 69.05: 记录段落改进快照
        new_avg = (
            sum(e["overall_quality"] for e in evaluations) / max(len(evaluations), 1)
        )
        self.tracker.log_section_improve_snapshot(
            round_num=state["section_improve_count"],
            improved_count=improved_count,
            avg_score_before=state.get("prev_section_avg_score", 0),
            avg_score_after=new_avg,
        )

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

        # 69.05: 记录配图生成结果
        for img in state.get('images', []):
            self.tracker.log_image_generation(
                image_id=img.get('id', ''),
                image_type=img.get('render_method', ''),
                success=True,
            )

        return state
    
    def _reviewer_node(self, state: SharedState) -> SharedState:
        """质量审核节点"""
        logger.info("=== Step 7: 质量审核 ===")
        state = self.reviewer.run(state)

        # 合并一致性检查发现的问题到 review_issues
        consistency_issues = state.get('thread_issues', []) + state.get('voice_issues', [])
        if consistency_issues:
            existing = state.get('review_issues', [])
            state['review_issues'] = existing + consistency_issues
            logger.info(f"[Reviewer] 合并一致性检查问题: {len(consistency_issues)} 条")

        # 69.05: 记录审核分数到 Langfuse
        self.tracker.log_review_score(
            score=state.get('review_score', 0),
            round_num=state.get('revision_count', 0),
            summary=f"issues={len(state.get('review_issues', []))} approved={state.get('review_approved', False)}",
        )

        return state
    
    def _revision_node(self, state: SharedState) -> SharedState:
        """修订节点（并行）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os
        
        logger.info("=== Step 7.1: 修订 ===")
        before_count = _get_content_word_count(state)
        state['revision_count'] = state.get('revision_count', 0) + 1
        
        # 根据审核问题修订内容
        review_issues = state.get('review_issues', [])
        total_issues = len(review_issues)
        style = self._get_style(state)

        if total_issues == 0:
            logger.info("没有需要修订的问题")
            return state
        
        max_workers = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))
        use_parallel = _should_use_parallel()
        
        # correct_only 模式：按章节分组问题，使用 correct_section（只更正不扩展）
        if style.revision_strategy == "correct_only":
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
            
            if use_parallel:
                logger.info(f"开始更正 {len(section_issues)} 个章节，使用 {min(max_workers, len(section_issues))} 个并行线程")
            else:
                logger.info(f"开始更正 {len(section_issues)} 个章节，使用串行模式（追踪已启用）")
            
            # 准备任务列表
            tasks = []
            for idx, (section_id, issues) in enumerate(section_issues.items(), 1):
                for section in state.get('sections', []):
                    if section.get('id') == section_id:
                        tasks.append({
                            'section': section,
                            'section_id': section_id,
                            'issues': issues,
                            'progress_info': f"[{idx}/{len(section_issues)}]"
                        })
                        break
            
            # 执行更正
            def correct_single_task(task):
                try:
                    section = task['section']
                    section_title = section.get('title', task['section_id'])
                    corrected_content = self.writer.correct_section(
                        original_content=section.get('content', ''),
                        issues=task['issues'],
                        section_title=section_title,
                        progress_info=task['progress_info']
                    )
                    return {
                        'success': True,
                        'section_id': task['section_id'],
                        'content': corrected_content
                    }
                except Exception as e:
                    logger.error(f"章节更正失败 [{task['section_id']}]: {e}")
                    return {
                        'success': False,
                        'section_id': task['section_id'],
                        'content': None
                    }
            
            if use_parallel:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(correct_single_task, task): task for task in tasks}
                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            for section in state.get('sections', []):
                                if section.get('id') == result['section_id']:
                                    section['content'] = result['content']
                                    break
            else:
                # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
                for task in tasks:
                    try:
                        section = task['section']
                        section_title = section.get('title', task['section_id'])
                        corrected_content = self.writer.correct_section(
                            original_content=section.get('content', ''),
                            issues=task['issues'],
                            section_title=section_title,
                            progress_info=task['progress_info']
                        )
                        for s in state.get('sections', []):
                            if s.get('id') == task['section_id']:
                                s['content'] = corrected_content
                                break
                    except Exception as e:
                        logger.error(f"章节更正失败 [{task['section_id']}]: {e}")
        else:
            # 其他模式：使用 enhance_section（可扩展内容）
            if use_parallel:
                logger.info(f"开始修订 {total_issues} 个问题，使用 {min(max_workers, total_issues)} 个并行线程")
            else:
                logger.info(f"开始修订 {total_issues} 个问题，使用串行模式（追踪已启用）")
            
            # 准备任务列表
            tasks = []
            for idx, issue in enumerate(review_issues, 1):
                section_id = issue.get('section_id', '')
                suggestion = issue.get('suggestion', '')
                
                for section in state.get('sections', []):
                    if section.get('id') == section_id:
                        tasks.append({
                            'section': section,
                            'section_id': section_id,
                            'issue': issue,
                            'suggestion': suggestion,
                            'progress_info': f"[{idx}/{total_issues}]"
                        })
                        break
            
            # 执行增强
            def enhance_single_task(task):
                try:
                    section = task['section']
                    section_title = section.get('title', task['section_id'])
                    enhanced_content = self.writer.enhance_section(
                        original_content=section.get('content', ''),
                        vague_points=[{
                            'location': section_title,
                            'issue': task['issue'].get('description', ''),
                            'question': task['suggestion'],
                            'suggestion': '根据审核建议修改'
                        }],
                        section_title=section_title,
                        progress_info=task['progress_info']
                    )
                    return {
                        'success': True,
                        'section_id': task['section_id'],
                        'content': enhanced_content
                    }
                except Exception as e:
                    logger.error(f"章节修订失败 [{task['section_id']}]: {e}")
                    return {
                        'success': False,
                        'section_id': task['section_id'],
                        'content': None
                    }
            
            if use_parallel:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(enhance_single_task, task): task for task in tasks}
                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            for section in state.get('sections', []):
                                if section.get('id') == result['section_id']:
                                    section['content'] = result['content']
                                    break
            else:
                # 串行执行（追踪模式）- 直接调用方法以保持 Langfuse 上下文
                for task in tasks:
                    try:
                        section = task['section']
                        section_title = section.get('title', task['section_id'])
                        enhanced_content = self.writer.enhance_section(
                            original_content=section.get('content', ''),
                            vague_points=[{
                                'location': section_title,
                                'issue': task['issue'].get('description', ''),
                                'question': task['suggestion'],
                                'suggestion': '根据审核建议修改'
                            }],
                            section_title=section_title,
                            progress_info=task['progress_info']
                        )
                        for s in state.get('sections', []):
                            if s.get('id') == task['section_id']:
                                s['content'] = enhanced_content
                                break
                    except Exception as e:
                        logger.error(f"章节修订失败 [{task['section_id']}]: {e}")
        
        after_count = _get_content_word_count(state)
        _log_word_count_diff("修订", before_count, after_count)
        return state

    def _consistency_check_node(self, state: SharedState) -> SharedState:
        """一致性检查节点（Thread + Voice 并行）"""
        from concurrent.futures import ThreadPoolExecutor

        sections = state.get('sections', [])
        if len(sections) < 2:
            state['thread_issues'] = []
            state['voice_issues'] = []
            return state

        style = self._get_style(state)
        thread_enabled = self._is_enabled(self._env_thread_check, style.enable_thread_check)
        voice_enabled = self._is_enabled(self._env_voice_check, style.enable_voice_check)

        if not thread_enabled and not voice_enabled:
            state['thread_issues'] = []
            state['voice_issues'] = []
            return state

        logger.info("=== Step 6.5: 一致性检查（叙事 + 语气）===")

        use_parallel = _should_use_parallel()

        if use_parallel and thread_enabled and voice_enabled:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                if thread_enabled:
                    futures.append(executor.submit(self.thread_checker.run, state))
                if voice_enabled:
                    futures.append(executor.submit(self.voice_checker.run, state))
                for f in futures:
                    f.result()
        else:
            if thread_enabled:
                try:
                    self.thread_checker.run(state)
                except Exception as e:
                    logger.error(f"[ThreadChecker] 异常: {e}")
                    state['thread_issues'] = []
            if voice_enabled:
                try:
                    self.voice_checker.run(state)
                except Exception as e:
                    logger.error(f"[VoiceChecker] 异常: {e}")
                    state['voice_issues'] = []

        if not thread_enabled:
            state['thread_issues'] = []
        if not voice_enabled:
            state['voice_issues'] = []

        thread_count = len(state.get('thread_issues', []))
        voice_count = len(state.get('voice_issues', []))
        logger.info(f"[ConsistencyCheck] 完成: 叙事问题 {thread_count}, 语气问题 {voice_count}")
        return state

    def _get_style(self, state: SharedState) -> StyleProfile:
        """获取当前运行的 StyleProfile（实例级 > state 级 > target_length 推断）"""
        if self.style:
            return self.style
        target_length = state.get('target_length', 'medium')
        return StyleProfile.from_target_length(target_length)

    def _is_enabled(self, env_flag: bool, style_flag: bool) -> bool:
        """环境变量 AND StyleProfile 双重开关"""
        return env_flag and style_flag

    def _factcheck_node(self, state: SharedState) -> SharedState:
        """事实核查节点"""
        style = self._get_style(state)
        if not self._is_enabled(self._env_factcheck, style.enable_fact_check):
            logger.info("=== Step 7.3: 事实核查（已禁用，跳过）===")
            return state
        logger.info("=== Step 7.3: 事实核查 ===")
        try:
            return self.factcheck.run(state)
        except Exception as e:
            logger.error(f"[FactCheck] 异常，降级跳过: {e}")
            return state

    def _text_cleanup_node(self, state: SharedState) -> SharedState:
        """确定性文本清理节点（纯正则，零 LLM）"""
        style = self._get_style(state)
        if not self._is_enabled(self._env_text_cleanup, style.enable_text_cleanup):
            logger.info("=== Step 7.4: 文本清理（已禁用，跳过）===")
            return state
        logger.info("=== Step 7.4: 确定性文本清理 ===")
        from utils.text_cleanup import apply_full_cleanup
        total_fixes = 0
        for section in state.get('sections', []):
            content = section.get('content', '')
            if not content:
                continue
            result = apply_full_cleanup(content)
            section['content'] = result['text']
            fixes = result['total_fixes']
            if fixes:
                logger.info(f"  [{section.get('title', '')}] 修复 {fixes} 处: {result['stats']}")
                total_fixes += fixes
        logger.info(f"[TextCleanup] 完成: 共修复 {total_fixes} 处")
        return state

    def _humanizer_node(self, state: SharedState) -> SharedState:
        """去 AI 味节点"""
        style = self._get_style(state)
        if not self._is_enabled(self._env_humanizer, style.enable_humanizer):
            logger.info("=== Step 7.5: 去 AI 味（已禁用，跳过）===")
            return state
        logger.info("=== Step 7.5: 去 AI 味 ===")
        try:
            return self.humanizer.run(state)
        except Exception as e:
            logger.error(f"[Humanizer] 异常，降级使用原始内容: {e}")
            return state

    def _summary_generator_node(self, state: SharedState) -> SharedState:
        """博客导读 + SEO 关键词生成节点"""
        style = self._get_style(state)
        if not self._is_enabled(self._env_summary, style.enable_summary_gen):
            logger.info("=== Step 9: 导读+SEO（已禁用，跳过）===")
            return state
        logger.info("=== Step 9: 导读 + SEO 关键词生成 ===")
        try:
            return self.summary_generator.run(state)
        except Exception as e:
            logger.error(f"[SummaryGenerator] 异常，降级跳过: {e}")
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
        """判断是否需要修订 — 由 StyleProfile 控制"""
        style = self._get_style(state)
        revision_count = state.get('revision_count', 0)

        # 达到最大修订轮数
        if revision_count >= style.max_revision_rounds:
            logger.info(f"已达到最大修订轮数 ({style.max_revision_rounds})，跳过修订")
            return "assemble"

        review_issues = state.get('review_issues', [])

        # 修订问题过滤（high_only 模式）
        if style.revision_severity_filter == "high_only":
            high_issues = [i for i in review_issues if i.get('severity') == 'high']
            if high_issues:
                logger.info(f"[{style.revision_severity_filter}] 只处理 {len(high_issues)} 个 high 级别问题")
                state['review_issues'] = high_issues
                return "revision"
            logger.info(f"[{style.revision_severity_filter}] 无 high 级别问题，跳过修订")
            return "assemble"

        # 完整修订模式
        if not state.get('review_approved', True):
            return "revision"

        logger.info("审核通过或修订完成，进入组装")
        return "assemble"

    def _should_refine_search(self, state: SharedState) -> Literal["search", "continue"]:
        """判断是否需要细化搜索 — 由 StyleProfile 控制"""
        style = self._get_style(state)
        if not style.enable_knowledge_refinement:
            logger.info("知识增强已禁用，跳过")
            return "continue"

        gaps = state.get('knowledge_gaps', [])
        search_count = state.get('search_count', 0)
        max_count = state.get('max_search_count', 5)

        if gaps and search_count < max_count:
            important_gaps = [g for g in gaps if g.get('gap_type') in ['missing_data', 'vague_concept']]
            if important_gaps:
                logger.info(f"检测到 {len(important_gaps)} 个重要知识空白，触发细化搜索")
                return "search"

        logger.info("无需细化搜索，继续到追问阶段")
        return "continue"

    def _run_derivative_skills(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """37.14/37.16 运行博客衍生物 Skills（MindMap/Flashcard/StudyNote）"""
        if os.environ.get('SKILL_DERIVATIVES_ENABLED', 'false').lower() != 'true':
            return {}
        try:
            from .skills.executor import SkillExecutor
            from .skills.registry import SkillRegistry
            # 确保 skills 已注册（导入触发 @register 装饰器）
            from .skills import mindmap, flashcard, study_note  # noqa: F401

            executor = SkillExecutor()
            markdown = final_state.get('final_markdown', '')
            if not markdown:
                return {}

            input_data = {"markdown": markdown, "topic": final_state.get('topic', '')}
            results = {}
            for skill_name in SkillRegistry.get_post_process_skills():
                try:
                    result = executor.execute(skill_name, input_data)
                    if result.get('success'):
                        results[skill_name] = result.get('output')
                        logger.info(f"🎯 衍生物 [{skill_name}] 生成完成")
                except Exception as e:
                    logger.warning(f"衍生物 [{skill_name}] 生成失败: {e}")
            return results
        except Exception as e:
            logger.warning(f"衍生物系统初始化失败: {e}")
            return {}

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

        # 创建 Token 追踪器并注入 LLMService
        token_tracker = None
        try:
            import os
            if os.environ.get('TOKEN_TRACKING_ENABLED', 'true').lower() == 'true':
                from utils.token_tracker import TokenTracker
                token_tracker = TokenTracker()
                self.llm.token_tracker = token_tracker
        except Exception:
            pass

        # 创建结构化任务日志
        task_log = None
        try:
            import os as _os
            if _os.environ.get('BLOG_TASK_LOG_ENABLED', 'true').lower() == 'true':
                from .utils.task_log import BlogTaskLog
                task_log = BlogTaskLog(
                    topic=topic,
                    article_type=article_type,
                    target_length=target_length,
                )
                self.task_log = task_log
        except Exception:
            pass

        # 创建 ToolManager 并注册现有工具（37.09）
        try:
            from utils.tool_manager import BlogToolManager
            tool_manager = BlogToolManager(task_log=task_log)
            if self.search_service:
                tool_manager.register(
                    "web_search", self.search_service.search,
                    description="搜索互联网获取背景知识", timeout=30,
                )
            self.tool_manager = tool_manager
        except Exception:
            pass

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

            # 输出 Token 用量摘要
            token_summary = None
            if token_tracker:
                logger.info(token_tracker.format_summary())
                token_summary = token_tracker.get_summary()

            # 完成任务日志
            if task_log:
                task_log.complete(
                    score=final_state.get('review_score', 0),
                    word_count=len(final_state.get('final_markdown', '')),
                    revision_rounds=final_state.get('revision_count', 0),
                )
                if token_summary:
                    task_log.token_summary = token_summary
                try:
                    task_log.save()
                except Exception as save_err:
                    logger.warning(f"任务日志保存失败: {save_err}")
                logger.info(task_log.get_summary())

            result = {
                "success": True,
                "markdown": final_state.get('final_markdown', ''),
                "outline": final_state.get('outline', {}),
                "sections_count": len(final_state.get('sections', [])),
                "images_count": len(final_state.get('images', [])),
                "code_blocks_count": len(final_state.get('code_blocks', [])),
                "review_score": final_state.get('review_score', 0),
                "seo_keywords": final_state.get('seo_keywords', []),
                "social_summary": final_state.get('social_summary', ''),
                "meta_description": final_state.get('meta_description', ''),
                "error": None
            }
            if token_summary:
                result["token_summary"] = token_summary

            # 37.14/37.16 博客衍生物生成（Skill 后处理）
            derivatives = self._run_derivative_skills(final_state)
            if derivatives:
                result["derivatives"] = derivatives

            return result
            
        except Exception as e:
            logger.error(f"博客生成失败: {e}", exc_info=True)
            if task_log:
                task_log.fail(str(e))
                try:
                    task_log.save()
                except Exception:
                    pass
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
