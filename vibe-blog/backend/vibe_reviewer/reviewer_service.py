"""
vibe-reviewer 主服务

提供教程评估的核心功能入口
"""
import os
import logging
import time
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

from .models.reviewer_models import (
    init_reviewer_tables,
    TutorialModel,
    ChapterModel,
    IssueModel,
    ImageModel,
)
from .schemas import (
    TutorialRequest,
    TutorialResponse,
    EvaluationStatus,
    ContentType,
)
from .git_service import GitService
from .preprocessing.document_processor import DocumentProcessor
from .preprocessing.image_extractor import ImageExtractor
from .pipeline.analyzer import ContentAnalyzer
from .pipeline.search_agent import SearchAgent
from .pipeline.reference_manager import ReferenceManager
from .pipeline.score_aggregator import ScoreAggregator
from .agents.questioner import Questioner
from .agents.depth_checker import DepthChecker
from .agents.quality_reviewer import QualityReviewer
from .agents.readability_checker import ReadabilityChecker
from .agents.improver import Improver

logger = logging.getLogger(__name__)

# 全局服务实例
_reviewer_service: Optional['ReviewerService'] = None


class ReviewerService:
    """
    vibe-reviewer 主服务
    
    负责协调教程评估的完整流程:
    1. Git 仓库克隆/拉取
    2. 文档预处理 (扫描 .md 文件)
    3. 图片多模态理解
    4. 搜索增强评估
    5. 多维度评分
    6. 可操作反馈生成
    """
    
    def __init__(self, llm_service=None, search_service=None, repos_dir: str = None):
        """
        初始化 ReviewerService
        
        Args:
            llm_service: LLM 服务实例 (复用 vibe-blog)
            search_service: 搜索服务实例 (复用 vibe-blog)
            repos_dir: Git 仓库本地存储目录
        """
        self.llm_service = llm_service
        self.search_service = search_service
        
        # 设置仓库存储目录
        if repos_dir is None:
            base_dir = Path(__file__).parent.parent
            repos_dir = str(base_dir / "data" / "repos")
        self.repos_dir = repos_dir
        
        # 确保目录存在
        try:
            Path(repos_dir).mkdir(parents=True, exist_ok=True)
        except (OSError, IOError):
            logger.warning(f"无法创建仓库目录: {repos_dir}")
        
        logger.info(f"ReviewerService 初始化完成, repos_dir={repos_dir}")
    
    def add_tutorial(self, request: TutorialRequest) -> TutorialResponse:
        """
        添加教程
        
        Args:
            request: 教程请求
            
        Returns:
            教程响应
        """
        # 检查是否已存在
        existing = TutorialModel.get_by_git_url(request.git_url)
        if existing:
            logger.info(f"教程已存在: {request.git_url}")
            return TutorialResponse(
                id=existing['id'],
                name=existing['name'],
                git_url=existing['git_url'],
                status=existing['status'],
                overall_score=existing['overall_score'] or 0,
                total_chapters=existing['total_chapters'] or 0,
                total_issues=existing['total_issues'] or 0,
                high_issues=existing['high_issues'] or 0,
                medium_issues=existing['medium_issues'] or 0,
                low_issues=existing['low_issues'] or 0,
                created_at=existing['created_at'],
                last_evaluated=existing['last_evaluated'],
            )
        
        # 从 URL 提取名称
        name = request.name
        if not name:
            name = request.git_url.rstrip('/').split('/')[-1]
            if name.endswith('.git'):
                name = name[:-4]
        
        # 创建教程记录
        tutorial_id = TutorialModel.create(
            name=name,
            git_url=request.git_url,
            branch=request.branch,
            enable_search=request.enable_search,
            max_search_rounds=request.max_search_rounds,
        )
        
        logger.info(f"教程已创建: id={tutorial_id}, name={name}")
        
        return TutorialResponse(
            id=tutorial_id,
            name=name,
            git_url=request.git_url,
            status=EvaluationStatus.PENDING.value,
        )
    
    def get_tutorial(self, tutorial_id: int) -> Optional[TutorialResponse]:
        """获取教程详情"""
        tutorial = TutorialModel.get_by_id(tutorial_id)
        if not tutorial:
            return None
        
        return TutorialResponse(
            id=tutorial['id'],
            name=tutorial['name'],
            git_url=tutorial['git_url'],
            status=tutorial['status'],
            overall_score=tutorial['overall_score'] or 0,
            total_chapters=tutorial['total_chapters'] or 0,
            total_issues=tutorial['total_issues'] or 0,
            high_issues=tutorial['high_issues'] or 0,
            medium_issues=tutorial['medium_issues'] or 0,
            low_issues=tutorial['low_issues'] or 0,
            created_at=tutorial['created_at'],
            last_evaluated=tutorial['last_evaluated'],
        )
    
    def list_tutorials(self) -> List[TutorialResponse]:
        """获取所有教程列表"""
        tutorials = TutorialModel.get_all()
        return [
            TutorialResponse(
                id=t['id'],
                name=t['name'],
                git_url=t['git_url'],
                status=t['status'],
                overall_score=t['overall_score'] or 0,
                total_chapters=t['total_chapters'] or 0,
                total_issues=t['total_issues'] or 0,
                high_issues=t['high_issues'] or 0,
                medium_issues=t['medium_issues'] or 0,
                low_issues=t['low_issues'] or 0,
                created_at=t['created_at'],
                last_evaluated=t['last_evaluated'],
            )
            for t in tutorials
        ]
    
    def delete_tutorial(self, tutorial_id: int) -> bool:
        """删除教程"""
        tutorial = TutorialModel.get_by_id(tutorial_id)
        if not tutorial:
            return False
        
        TutorialModel.delete(tutorial_id)
        logger.info(f"教程已删除: id={tutorial_id}")
        return True
    
    def get_chapters(self, tutorial_id: int) -> List[Dict]:
        """获取教程的所有章节"""
        return ChapterModel.get_by_tutorial(tutorial_id)
    
    def get_chapter(self, chapter_id: int) -> Optional[Dict]:
        """获取章节详情"""
        return ChapterModel.get_by_id(chapter_id)
    
    def get_issues(self, tutorial_id: int = None, chapter_id: int = None, 
                   severity: str = None) -> List[Dict]:
        """获取问题列表"""
        if chapter_id:
            return IssueModel.get_by_chapter(chapter_id)
        elif tutorial_id:
            return IssueModel.get_by_tutorial(tutorial_id, severity)
        return []
    
    def mark_issue_resolved(self, issue_id: int, resolved: bool = True) -> bool:
        """标记问题已解决"""
        IssueModel.mark_resolved(issue_id, resolved)
        return True
    
    def evaluate_tutorial_sync(
        self, 
        tutorial_id: int,
        on_progress: Callable[[Dict], None] = None,
        max_chapters: int = 50,
        force_reevaluate: bool = False
    ) -> Dict:
        """
        评估教程 (同步版本)
        
        Args:
            tutorial_id: 教程 ID
            on_progress: 进度回调函数
            max_chapters: 最大评估章节数
            force_reevaluate: 强制重新评估（忽略增量更新）
            
        Returns:
            评估结果
        """
        start_time = time.time()
        tutorial = TutorialModel.get_by_id(tutorial_id)
        if not tutorial:
            raise ValueError(f"教程不存在: {tutorial_id}")
        
        def emit(event_type: str, **data):
            """发送进度事件"""
            if on_progress:
                on_progress({"type": event_type, **data})
        
        try:
            # ========== Step 1: Git 克隆/拉取 ==========
            TutorialModel.update_status(tutorial_id, EvaluationStatus.CLONING.value)
            emit("log", level="info", message=f"📥 开始克隆仓库: {tutorial['git_url']}")
            emit("status", status="cloning", message="正在克隆仓库...")
            
            git_service = GitService(self.repos_dir)
            local_path, has_update = git_service.clone_or_pull(
                tutorial['git_url'], 
                tutorial.get('branch', 'main')
            )
            
            emit("log", level="success", message=f"✅ 仓库克隆完成: {local_path}")
            emit("clone_complete", local_path=local_path, has_update=has_update)
            logger.info(f"仓库克隆完成: {local_path}")
            
            # ========== Step 2: 扫描 .md 文件 ==========
            TutorialModel.update_status(tutorial_id, EvaluationStatus.SCANNING.value)
            emit("log", level="info", message="🔍 开始扫描 Markdown 文件...")
            emit("status", status="scanning", message="正在扫描 Markdown 文件...")
            
            doc_processor = DocumentProcessor()
            md_files = doc_processor.scan_directory(local_path)
            
            emit("log", level="info", message=f"📄 发现 {len(md_files)} 个 Markdown 文件")
            
            # 限制章节数量
            if len(md_files) > max_chapters:
                emit("log", level="warning", message=f"⚠️ 章节数量超过限制，只评估前 {max_chapters} 个")
                logger.warning(f"章节数量 {len(md_files)} 超过限制 {max_chapters}，只评估前 {max_chapters} 个")
                md_files = md_files[:max_chapters]
            
            emit("log", level="success", message=f"✅ 扫描完成: 准备评估 {len(md_files)} 个章节")
            emit("scan_complete", total_files=len(md_files), 
                 files=[f.file_path for f in md_files])
            logger.info(f"扫描完成: 找到 {len(md_files)} 个 Markdown 文件")
            
            # ========== Step 3: 创建/更新章节记录 ==========
            chapters_to_evaluate = []
            for idx, md_file in enumerate(md_files):
                # 检查是否已存在且内容未变化 (增量更新)
                # force_reevaluate 只对当前选中的章节生效（前 max_chapters 个）
                should_force = force_reevaluate and idx < max_chapters
                
                if not should_force:
                    existing = ChapterModel.get_by_hash(tutorial_id, md_file.content_hash)
                    if existing and existing.get('status') == 'completed':
                        emit("log", level="info", message=f"   ⏭️ 章节未变化，跳过: {md_file.file_path}")
                        logger.debug(f"章节未变化，跳过: {md_file.file_path}")
                        continue
                
                # 创建或更新章节
                chapter_id = ChapterModel.create(
                    tutorial_id=tutorial_id,
                    file_path=md_file.file_path,
                    file_name=md_file.file_name,
                    title=md_file.title,
                    chapter_order=md_file.order,
                    raw_content=md_file.content,
                    content_hash=md_file.content_hash,
                )
                
                # 删除该章节的旧问题（重新评估时覆盖）
                IssueModel.delete_by_chapter(chapter_id)
                
                chapters_to_evaluate.append({
                    'id': chapter_id,
                    'file_path': md_file.file_path,
                    'title': md_file.title,
                    'content': md_file.content,
                    'base_path': os.path.dirname(os.path.join(local_path, md_file.file_path)),
                })
            
            emit("chapters_ready", total=len(chapters_to_evaluate))
            
            # ========== Step 4: 逐章评估 ==========
            TutorialModel.update_status(tutorial_id, EvaluationStatus.EVALUATING.value)
            
            # 初始化评估组件
            analyzer = ContentAnalyzer(self.llm_service) if self.llm_service else None
            search_agent = SearchAgent(self.search_service)
            ref_manager = ReferenceManager(self.llm_service)
            questioner = Questioner(self.llm_service) if self.llm_service else None
            depth_checker = DepthChecker(self.llm_service) if self.llm_service else None
            quality_reviewer = QualityReviewer(self.llm_service) if self.llm_service else None
            readability_checker = ReadabilityChecker(self.llm_service) if self.llm_service else None
            improver = Improver(self.llm_service) if self.llm_service else None
            score_aggregator = ScoreAggregator()
            image_extractor = ImageExtractor()
            
            total_issues = 0
            high_issues = 0
            medium_issues = 0
            low_issues = 0
            total_score = 0
            
            # ========== Step 4.0: 生成章节摘要（用于上下文连贯性检测）==========
            emit("log", level="info", message="📝 正在生成章节摘要...")
            chapter_summaries = []
            for idx, chapter in enumerate(chapters_to_evaluate):
                # 使用 LLM 生成简短摘要
                if self.llm_service:
                    try:
                        summary_prompt = f"请用1-2句话概括以下内容的核心主题和要点（不超过100字）：\n\n{chapter['content'][:2000]}"
                        chapter_summary = self.llm_service.chat(
                            messages=[{"role": "user", "content": summary_prompt}]
                        )
                        chapter_summaries.append({
                            'title': chapter['title'] or chapter['file_path'],
                            'summary': chapter_summary[:200] if chapter_summary else ''
                        })
                    except Exception as e:
                        logger.warning(f"生成章节摘要失败: {e}")
                        chapter_summaries.append({
                            'title': chapter['title'] or chapter['file_path'],
                            'summary': ''
                        })
                else:
                    chapter_summaries.append({
                        'title': chapter['title'] or chapter['file_path'],
                        'summary': ''
                    })
            emit("log", level="success", message=f"✅ 章节摘要生成完成: {len(chapter_summaries)} 个")
            
            for idx, chapter in enumerate(chapters_to_evaluate):
                chapter_id = chapter['id']
                content = chapter['content']
                
                # 构建上下文信息（前一章和后一章的摘要）
                context = {
                    'prev_chapter': chapter_summaries[idx - 1] if idx > 0 else None,
                    'next_chapter': chapter_summaries[idx + 1] if idx < len(chapter_summaries) - 1 else None,
                    'chapter_index': idx + 1,
                    'total_chapters': len(chapters_to_evaluate),
                }
                
                emit("chapter_start", 
                     chapter_id=chapter_id, 
                     chapter_index=idx + 1,
                     total_chapters=len(chapters_to_evaluate),
                     file_path=chapter['file_path'])
                emit("log", level="info", message=f"📖 [{idx+1}/{len(chapters_to_evaluate)}] 开始评估: {chapter['title'] or chapter['file_path']}")
                
                try:
                    # 4.1 内容分析
                    emit("log", level="info", message="   🔬 正在分析内容结构...")
                    emit("chapter_step", chapter_id=chapter_id, step="analyze", status="start")
                    summary = analyzer.analyze(content) if analyzer else None
                    content_type = summary.content_type if summary else ContentType.UNKNOWN
                    emit("chapter_step", chapter_id=chapter_id, step="analyze", status="complete")
                    if summary:
                        emit("log", level="info", message=f"   ✓ 内容分析完成: 类型={content_type.value}, 主题={summary.topic[:30] if summary.topic else '未知'}...")
                    
                    # 4.2 搜索参考资料 (如果启用)
                    references = []
                    if tutorial.get('enable_search', True) and summary and summary.search_queries:
                        emit("log", level="info", message=f"   🔎 正在搜索参考资料 (关键词: {', '.join(summary.search_queries[:3])})")
                        emit("chapter_step", chapter_id=chapter_id, step="search", status="start")
                        search_results = search_agent.search_multi_round(
                            summary, 
                            max_rounds=tutorial.get('max_search_rounds', 2)
                        )
                        # 评估相关性
                        search_results = ref_manager.evaluate_relevance(search_results, summary)
                        references = ref_manager.get_top_references(search_results, top_k=5)
                        emit("chapter_step", chapter_id=chapter_id, step="search", status="complete",
                             results_count=len(references))
                        emit("log", level="info", message=f"   ✓ 搜索完成: 找到 {len(references)} 条相关参考")
                    
                    # 4.3 追问检查（发现模糊点和遗漏，包含上下文连贯性检测）
                    emit("log", level="info", message="   ❓ 正在进行追问检查...")
                    emit("chapter_step", chapter_id=chapter_id, step="question", status="start")
                    question_result = questioner.question(content, context=context) if questioner else None
                    emit("chapter_step", chapter_id=chapter_id, step="question", status="complete")
                    if question_result:
                        emit("log", level="info", message=f"   ✓ 追问检查完成: 评分={question_result.get('score', 70)}, 模糊点={len(question_result.get('issues', []))}")
                    
                    # 4.4 深度检查
                    emit("log", level="info", message="   📊 正在进行深度检查...")
                    emit("chapter_step", chapter_id=chapter_id, step="depth", status="start")
                    depth_result = depth_checker.check(content, references) if depth_checker else None
                    emit("chapter_step", chapter_id=chapter_id, step="depth", status="complete")
                    if depth_result:
                        emit("log", level="info", message=f"   ✓ 深度检查完成: 评分={depth_result.score}, 模糊点={len(depth_result.vague_points)}")
                    
                    # 4.4 质量审核
                    emit("log", level="info", message="   ✅ 正在进行质量审核...")
                    emit("chapter_step", chapter_id=chapter_id, step="quality", status="start")
                    quality_result = quality_reviewer.review(content, references) if quality_reviewer else None
                    emit("chapter_step", chapter_id=chapter_id, step="quality", status="complete")
                    if quality_result:
                        emit("log", level="info", message=f"   ✓ 质量审核完成: 评分={quality_result.score}, 问题={len(quality_result.issues)}")
                    
                    # 4.5 可读性检测
                    emit("log", level="info", message="   📖 正在检测可读性...")
                    emit("chapter_step", chapter_id=chapter_id, step="readability", status="start")
                    readability_result = readability_checker.check(content) if readability_checker else None
                    emit("chapter_step", chapter_id=chapter_id, step="readability", status="complete")
                    if readability_result:
                        emit("log", level="info", message=f"   ✓ 可读性检测完成: 评分={readability_result.score}, 级别={readability_result.level.value}")
                    
                    # 4.6 生成改进建议
                    feedback = []
                    if improver and depth_result and quality_result and readability_result:
                        emit("log", level="info", message="   💡 正在生成改进建议...")
                        emit("chapter_step", chapter_id=chapter_id, step="improve", status="start")
                        feedback = improver.generate(content, depth_result, quality_result, readability_result)
                        emit("chapter_step", chapter_id=chapter_id, step="improve", status="complete")
                        emit("log", level="info", message=f"   ✓ 改进建议生成完成: {len(feedback)} 条建议")
                    
                    # 4.7 计算综合评分
                    if depth_result and quality_result and readability_result:
                        overall_score, dimension_scores = score_aggregator.aggregate(
                            depth_result, quality_result, readability_result, content_type
                        )
                    else:
                        overall_score = 70
                        dimension_scores = None
                    
                    # 4.8 统计问题
                    chapter_issues = []
                    
                    # 追问检查的问题
                    if question_result:
                        for issue in question_result.get('issues', []):
                            chapter_issues.append({
                                'category': 'questioner',
                                'issue_type': issue.issue_type if hasattr(issue, 'issue_type') else 'vague_claim',
                                'severity': issue.severity if hasattr(issue, 'severity') else 'medium',
                                'location': issue.location if hasattr(issue, 'location') else '',
                                'original_text': issue.original_text if hasattr(issue, 'original_text') else '',
                                'description': issue.description if hasattr(issue, 'description') else '',
                                'suggestion': issue.suggestion if hasattr(issue, 'suggestion') else '',
                            })
                    
                    # 深度检查的问题
                    if depth_result:
                        for vp in depth_result.vague_points:
                            chapter_issues.append({
                                'category': 'depth',
                                'issue_type': 'vague_claim',
                                'severity': 'medium',
                                'location': vp.location,
                                'original_text': vp.original_text if hasattr(vp, 'original_text') else '',
                                'description': vp.issue,
                                'suggestion': vp.suggestion,
                            })
                    
                    if quality_result:
                        for issue in quality_result.issues:
                            chapter_issues.append({
                                'category': 'quality',
                                'issue_type': issue.issue_type,
                                'severity': issue.severity,
                                'location': issue.location,
                                'original_text': issue.original_text if hasattr(issue, 'original_text') else '',
                                'description': issue.description,
                                'suggestion': issue.suggestion,
                                'reference': issue.reference,
                            })
                    
                    if readability_result:
                        for issue in readability_result.issues:
                            chapter_issues.append({
                                'category': 'readability',
                                'issue_type': issue.issue_type,
                                'severity': issue.severity,
                                'location': issue.location,
                                'original_text': issue.original_text if hasattr(issue, 'original_text') else '',
                                'description': issue.description,
                                'suggestion': issue.suggestion,
                            })
                    
                    # 4.9 保存问题到数据库
                    chapter_high = 0
                    chapter_medium = 0
                    chapter_low = 0
                    for issue in chapter_issues:
                        IssueModel.create(
                            chapter_id=chapter_id,
                            tutorial_id=tutorial_id,
                            **issue
                        )
                        if issue['severity'] == 'high':
                            chapter_high += 1
                        elif issue['severity'] == 'medium':
                            chapter_medium += 1
                        else:
                            chapter_low += 1
                    
                    # 4.10 更新章节评分
                    ChapterModel.update_scores(
                        chapter_id=chapter_id,
                        overall_score=overall_score,
                        depth_score=depth_result.score if depth_result else 70,
                        quality_score=quality_result.score if quality_result else 70,
                        readability_score=readability_result.score if readability_result else 70,
                        readability_level=readability_result.level.value if readability_result else 'normal',
                        total_issues=len(chapter_issues),
                        high_issues=chapter_high,
                        medium_issues=chapter_medium,
                        low_issues=chapter_low,
                    )
                    
                    # 累计统计
                    total_issues += len(chapter_issues)
                    high_issues += chapter_high
                    medium_issues += chapter_medium
                    low_issues += chapter_low
                    total_score += overall_score
                    
                    # 推送章节完成日志
                    score_color = "🟢" if overall_score >= 80 else "🟡" if overall_score >= 60 else "🔴"
                    emit("log", level="success", 
                         message=f"   {score_color} 章节评估完成: 综合评分={overall_score}, 问题数={len(chapter_issues)} (🔴{chapter_high} 🟡{chapter_medium} 🟢{chapter_low})")
                    
                    # 推送章节完成事件 (包含问题详情)
                    emit("chapter_complete",
                         chapter_id=chapter_id,
                         chapter_index=idx + 1,
                         total_chapters=len(chapters_to_evaluate),
                         file_path=chapter['file_path'],
                         title=chapter['title'],
                         overall_score=overall_score,
                         depth_score=depth_result.score if depth_result else 70,
                         quality_score=quality_result.score if quality_result else 70,
                         readability_score=readability_result.score if readability_result else 70,
                         total_issues=len(chapter_issues),
                         high_issues=chapter_high,
                         medium_issues=chapter_medium,
                         low_issues=chapter_low,
                         issues=chapter_issues[:5])  # 只推送前5个问题，避免数据过大
                    
                except Exception as e:
                    logger.error(f"章节评估失败: {chapter['file_path']}, 错误: {e}")
                    emit("log", level="error", message=f"   ❌ 章节评估失败: {str(e)}")
                    emit("chapter_error", chapter_id=chapter_id, error=str(e))
            
            # ========== Step 5: 汇总结果 ==========
            emit("log", level="info", message="📊 正在汇总评估结果...")
            duration = int(time.time() - start_time)
            avg_score = total_score / len(chapters_to_evaluate) if chapters_to_evaluate else 0
            
            TutorialModel.update_scores(
                tutorial_id=tutorial_id,
                overall_score=avg_score,
                avg_depth=avg_score,  # 简化处理
                avg_quality=avg_score,
                avg_readability=avg_score,
                total_chapters=len(md_files),
                total_issues=total_issues,
                high_issues=high_issues,
                medium_issues=medium_issues,
                low_issues=low_issues,
            )
            
            TutorialModel.update_status(tutorial_id, EvaluationStatus.COMPLETED.value)
            
            emit("log", level="success", message=f"🎉 评估完成!")
            emit("log", level="info", message=f"   📈 综合评分: {avg_score:.1f}")
            emit("log", level="info", message=f"   📚 评估章节: {len(chapters_to_evaluate)}/{len(md_files)}")
            emit("log", level="info", message=f"   🔍 发现问题: {total_issues} (🔴{high_issues} 🟡{medium_issues} 🟢{low_issues})")
            emit("log", level="info", message=f"   ⏱️ 耗时: {duration} 秒")
            
            emit("evaluation_complete",
                 tutorial_id=tutorial_id,
                 overall_score=avg_score,
                 total_chapters=len(md_files),
                 evaluated_chapters=len(chapters_to_evaluate),
                 total_issues=total_issues,
                 duration_seconds=duration)
            
            logger.info(f"评估完成: tutorial_id={tutorial_id}, score={avg_score:.1f}, issues={total_issues}, duration={duration}s")
            
            return {
                "success": True,
                "tutorial_id": tutorial_id,
                "overall_score": avg_score,
                "total_chapters": len(md_files),
                "evaluated_chapters": len(chapters_to_evaluate),
                "total_issues": total_issues,
                "high_issues": high_issues,
                "medium_issues": medium_issues,
                "low_issues": low_issues,
                "duration_seconds": duration,
            }
            
        except Exception as e:
            logger.error(f"评估失败: {e}", exc_info=True)
            TutorialModel.update_status(tutorial_id, EvaluationStatus.FAILED.value, str(e))
            emit("error", message=str(e))
            raise
    
    async def evaluate_tutorial(
        self, 
        tutorial_id: int,
        on_progress: Callable[[Dict], None] = None
    ) -> Dict:
        """
        评估教程 (异步包装)
        
        Args:
            tutorial_id: 教程 ID
            on_progress: 进度回调函数
            
        Returns:
            评估结果
        """
        # 调用同步版本
        return self.evaluate_tutorial_sync(tutorial_id, on_progress)


def init_reviewer_service(llm_service=None, search_service=None, repos_dir: str = None):
    """
    初始化 ReviewerService
    
    Args:
        llm_service: LLM 服务实例
        search_service: 搜索服务实例
        repos_dir: Git 仓库存储目录
    """
    global _reviewer_service
    
    # 初始化数据库
    init_reviewer_tables()
    
    # 创建服务实例
    _reviewer_service = ReviewerService(
        llm_service=llm_service,
        search_service=search_service,
        repos_dir=repos_dir,
    )
    
    return _reviewer_service


def get_reviewer_service() -> Optional[ReviewerService]:
    """获取 ReviewerService 实例"""
    return _reviewer_service
