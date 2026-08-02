"""
长文博客生成器 - LangGraph 工作流主入口
"""

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Dict, Any, Optional, Literal, Callable

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from .schemas.state import SharedState
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
from .middleware import (
    MiddlewarePipeline, TracingMiddleware, ReducerMiddleware,
    ErrorTrackingMiddleware, TokenBudgetMiddleware, ContextPrefetchMiddleware,
    TaskLogMiddleware,
    ErrorTrackingMiddleware, TokenBudgetMiddleware, ContextPrefetchMiddleware,
)
from .context_management_middleware import ContextManagementMiddleware
from .parallel import ParallelTaskExecutor, TaskConfig
from .llm_proxy import TieredLLMProxy
from .llm_tier_config import get_agent_tier
from .orchestrator.execution_runner import GraphExecutionRunner
from .orchestrator.graph_builder import GraphBuilder
from .orchestrator.image_task_registry import ImageTaskRegistry
from .orchestrator.nodes.finalization import (
    assembler_node,
    coder_and_artist_node,
    factcheck_node,
    humanizer_node,
    summary_generator_node,
    text_cleanup_node,
    wait_for_images_node,
)
from .orchestrator.nodes.research import (
    check_knowledge_node,
    enhance_with_knowledge_node,
    planner_node,
    refine_search_node,
    researcher_node,
)
from .orchestrator.nodes.review import (
    consistency_check_node,
    cross_section_dedup_node,
    reviewer_node,
    revision_node,
)
from .orchestrator.nodes.writing import (
    deepen_content_node,
    questioner_node,
    section_evaluate_node,
    section_improve_node,
    writer_node,
)
from .cross_section_dedup import CrossSectionDeduplicator
from .image_preplanner import ImagePreplanner
from .prompts import get_prompt_manager
from utils.text_cleanup import apply_full_cleanup

logger = logging.getLogger(__name__)


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

        # 初始化各 Agent（41.06: 通过 TieredLLMProxy 按级别路由模型）
        def _proxy(agent_name):
            return TieredLLMProxy(llm_client, get_agent_tier(agent_name))

        self.researcher = ResearcherAgent(_proxy('researcher'), search_service, knowledge_service)
        self.planner = PlannerAgent(_proxy('planner'))
        self.writer = WriterAgent(_proxy('writer'))
        self.coder = CoderAgent(_proxy('coder'))
        self.artist = ArtistAgent(_proxy('artist'))
        self.questioner = QuestionerAgent(_proxy('questioner'))
        self.reviewer = ReviewerAgent(_proxy('reviewer'))
        self.assembler = AssemblerAgent()
        self.search_coordinator = SearchCoordinator(_proxy('search_coordinator'), search_service)

        # 增强 Agent：环境变量作为全局开关（StyleProfile 作为运行时开关）
        self._env_humanizer = os.getenv('HUMANIZER_ENABLED', 'true').lower() == 'true'
        self._env_thread_check = os.getenv('THREAD_CHECK_ENABLED', 'true').lower() == 'true'
        self._env_voice_check = os.getenv('VOICE_CHECK_ENABLED', 'true').lower() == 'true'
        self._env_factcheck = os.getenv('FACTCHECK_ENABLED', 'true').lower() == 'true'
        self._env_text_cleanup = os.getenv('TEXT_CLEANUP_ENABLED', 'true').lower() == 'true'
        self._env_summary = os.getenv('SUMMARY_GENERATOR_ENABLED', 'true').lower() == 'true'

        # 初始化增强 Agent（只要环境变量没禁用就创建实例）
        self.humanizer = HumanizerAgent(_proxy('humanizer')) if self._env_humanizer else None
        self.thread_checker = ThreadCheckerAgent(_proxy('thread_checker')) if self._env_thread_check else None
        self.voice_checker = VoiceCheckerAgent(_proxy('voice_checker')) if self._env_voice_check else None
        self.factcheck = FactCheckAgent(_proxy('factcheck')) if self._env_factcheck else None

        # 业务级状态追踪（69.05）
        self.tracker = SessionTracker()
        self.summary_generator = SummaryGeneratorAgent(_proxy('summary_generator')) if self._env_summary else None

        # Future stays outside SharedState so checkpoint serialization remains stable.
        self._image_task_registry = ImageTaskRegistry()

        # 37.12 分层架构校验器（可选）
        self._layer_validator = None
        if os.environ.get('LAYER_VALIDATION_ENABLED', 'false').lower() == 'true':
            try:
                from .orchestrator.layer_definitions import BLOG_LAYERS, LayerValidator
                self._layer_validator = LayerValidator(BLOG_LAYERS)
                logger.info("🏗️ 分层架构校验已启用")
            except Exception as e:
                logger.warning(f"分层架构校验初始化失败: {e}")

        # 102.10 迁移：中间件管道
        self._task_log_middleware = TaskLogMiddleware()
        self.pipeline = MiddlewarePipeline(middlewares=[
            TracingMiddleware(),
            self._task_log_middleware,
            ReducerMiddleware(),
            ErrorTrackingMiddleware(),
            ContextManagementMiddleware(
                llm_service=llm_client,
                model_name=os.getenv("LLM_MODEL", "gpt-4o"),
            ),
            TokenBudgetMiddleware(
                compressor=getattr(self, '_context_compressor', None),
                token_tracker=getattr(self, '_token_tracker', None),
            ),
            ContextPrefetchMiddleware(
                knowledge_service=knowledge_service,
            ),
        ])

        # 102.01 迁移：统一并行任务执行引擎
        self.executor = ParallelTaskExecutor()

        # 102.06 迁移：写作方法论技能管理器
        self._writing_skill_manager = None
        if os.getenv('WRITING_SKILL_ENABLED', 'true').lower() == 'true':
            try:
                from .skills.writing_skill_manager import WritingSkillManager
                self._writing_skill_manager = WritingSkillManager()
                self._writing_skill_manager.load()
                logger.info("102.06 WritingSkillManager 已启用")
            except Exception as e:
                logger.warning(f"WritingSkillManager 初始化失败: {e}")

        # 102.03 迁移：用户记忆存储
        self._memory_storage = None
        if os.getenv('MEMORY_ENABLED', 'false').lower() == 'true':
            try:
                from .memory import MemoryStorage, BlogMemoryConfig
                mem_config = BlogMemoryConfig.from_env()
                self._memory_storage = MemoryStorage(storage_path=mem_config.storage_path)
                logger.info("102.03 MemoryStorage 已启用")
            except Exception as e:
                logger.warning(f"MemoryStorage 初始化失败: {e}")

        # 构建工作流
        self.workflow = self._build_workflow()
        self.app = None
        self._execution_runner = GraphExecutionRunner(self)

    def _build_workflow(self) -> StateGraph:
        """
        构建 LangGraph 工作流
        
        Returns:
            StateGraph 实例
        """
        self._node_handlers = self._bind_node_handlers()
        return GraphBuilder(
            node_handlers=self._node_handlers,
            routing_handlers=self._bind_routing_handlers(),
            middleware_pipeline=self.pipeline,
        ).build()

    def _bind_node_handlers(self):
        return {
            "researcher": partial(
                researcher_node,
                researcher=self.researcher,
                layer_validator=self._layer_validator,
            ),
            "planner": partial(
                planner_node,
                planner=self.planner,
                layer_validator=self._layer_validator,
                on_stream=None,
                interactive=False,
                writing_skill_manager=self._writing_skill_manager,
                llm_client=self.llm,
                interrupt_fn=interrupt,
                getenv=os.getenv,
                image_preplanner_factory=ImagePreplanner,
            ),
            "writer": partial(
                writer_node,
                writer=self.writer,
                layer_validator=self._layer_validator,
                memory_storage=self._memory_storage,
                configured_style=self.style,
            ),
            "check_knowledge": partial(
                check_knowledge_node,
                search_coordinator=self.search_coordinator,
            ),
            "refine_search": partial(
                refine_search_node,
                search_coordinator=self.search_coordinator,
            ),
            "enhance_with_knowledge": partial(
                enhance_with_knowledge_node,
                writer=self.writer,
                parallel_executor=self.executor,
                prompt_manager_factory=get_prompt_manager,
                task_config_factory=TaskConfig,
            ),
            "questioner": partial(questioner_node, questioner=self.questioner),
            "deepen_content": partial(
                deepen_content_node,
                writer=self.writer,
                parallel_executor=self.executor,
                tracker=self.tracker,
                task_config_factory=TaskConfig,
            ),
            "section_evaluate": partial(
                section_evaluate_node,
                questioner=self.questioner,
                tracker=self.tracker,
                configured_style=self.style,
            ),
            "section_improve": partial(
                section_improve_node,
                writer=self.writer,
                tracker=self.tracker,
            ),
            "coder_and_artist": partial(
                coder_and_artist_node,
                coder=self.coder,
                artist=self.artist,
                image_task_registry=self._image_task_registry,
                executor_factory=ThreadPoolExecutor,
                uuid_factory=lambda: str(uuid.uuid4()),
            ),
            "cross_section_dedup": partial(
                cross_section_dedup_node,
                getenv=os.getenv,
                deduplicator_factory=CrossSectionDeduplicator,
                llm_client=self.llm,
            ),
            "consistency_check": partial(
                consistency_check_node,
                configured_style=self.style,
                env_thread_check=self._env_thread_check,
                env_voice_check=self._env_voice_check,
                thread_checker=self.thread_checker,
                voice_checker=self.voice_checker,
                parallel_executor=self.executor,
                task_config_factory=TaskConfig,
            ),
            "reviewer": partial(
                reviewer_node,
                reviewer=self.reviewer,
                tracker=self.tracker,
                configured_style=self.style,
            ),
            "revision": partial(
                revision_node,
                writer=self.writer,
                parallel_executor=self.executor,
                configured_style=self.style,
                task_config_factory=TaskConfig,
            ),
            "factcheck": partial(
                factcheck_node,
                factcheck=self.factcheck,
                configured_style=self.style,
                env_factcheck=self._env_factcheck,
            ),
            "text_cleanup": partial(
                text_cleanup_node,
                cleanup=apply_full_cleanup,
                configured_style=self.style,
                env_text_cleanup=self._env_text_cleanup,
            ),
            "humanizer": partial(
                humanizer_node,
                humanizer=self.humanizer,
                configured_style=self.style,
                env_humanizer=self._env_humanizer,
            ),
            "wait_for_images": partial(
                wait_for_images_node,
                image_task_registry=self._image_task_registry,
                tracker=self.tracker,
                timeout=600,
            ),
            "assembler": partial(assembler_node, assembler=self.assembler),
            "summary_generator": partial(
                summary_generator_node,
                summary_generator=self.summary_generator,
                configured_style=self.style,
                env_summary=self._env_summary,
            ),
        }

    def _bind_routing_handlers(self):
        return {
            "should_check_knowledge": self._should_check_knowledge,
            "should_refine_search": self._should_refine_search,
            "should_deepen": self._should_deepen,
            "should_continue_questioning": self._should_continue_questioning,
            "should_improve_sections": self._should_improve_sections,
            "should_revise": self._should_revise,
        }

    def _configure_planner_runtime(self, *, on_stream, interactive):
        planner_handler = self._node_handlers["planner"]
        planner_handler.keywords["on_stream"] = on_stream
        planner_handler.keywords["interactive"] = interactive

    def _configure_execution_runtime(self, executor):
        self.executor = executor
        for node_name in (
            "enhance_with_knowledge",
            "deepen_content",
            "consistency_check",
            "revision",
        ):
            self._node_handlers[node_name].keywords["parallel_executor"] = executor
    

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


    def _get_style(self, state: SharedState) -> StyleProfile:
        """获取当前运行的 StyleProfile（实例级 > state 级 > target_length 推断）"""
        if self.style:
            return self.style
        target_length = state.get('target_length', 'medium')
        return StyleProfile.from_target_length(target_length)

    def _build_config(self, state: dict) -> dict:
        """构建 LangGraph 执行配置，动态计算 recursion_limit"""
        style = self._get_style(state)
        base_nodes = 20  # _build_workflow() 实际节点数，新增节点时需同步更新
        max_loops = (
            style.max_questioning_rounds * 2
            + style.max_revision_rounds * 2
            + 2  # section_evaluate <-> improve
        )
        recursion_limit = base_nodes + max_loops + 5

        return {
            "configurable": {"thread_id": f"blog_{state.get('topic', 'default')}"},
            "recursion_limit": recursion_limit,
        }


    def _should_deepen(self, state: SharedState) -> Literal["deepen", "continue"]:
        """判断是否需要深化内容 — 统一用 StyleProfile 控制"""
        count = state.get('questioning_count', 0)
        style = self._get_style(state)
        max_rounds = style.max_questioning_rounds

        if count >= max_rounds:
            logger.info(f"[Deepen] 已达最大轮数 {count}/{max_rounds}，停止深化")
            return "continue"

        if not state.get('all_sections_detailed', True):
            logger.info(f"[Deepen] 第 {count+1}/{max_rounds} 轮深化")
            return "deepen"

        return "continue"

    def _should_continue_questioning(self, state: SharedState) -> Literal["questioner", "section_evaluate"]:
        """深化后判断是否需要继续追问 — 避免已达轮数上限仍执行 questioner"""
        count = state.get('questioning_count', 0)
        style = self._get_style(state)
        max_rounds = style.max_questioning_rounds
        if count >= max_rounds:
            logger.info(f"[Deepen] 深化后已达最大轮数 {count}/{max_rounds}，跳过追问")
            return "section_evaluate"
        return "questioner"

    def _should_check_knowledge(self, state: SharedState) -> Literal["check", "skip"]:
        """mini 模式跳过知识空白检查"""
        target_length = state.get('target_length', 'medium')
        if target_length == 'mini':
            logger.info("[check_knowledge] mini 模式，跳过知识空白检查")
            return "skip"
        return "check"

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
        return self._execution_runner.generate(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material,
            on_progress=on_progress,
        )
    
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
        async for event in self._execution_runner.generate_stream(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material,
        ):
            yield event
