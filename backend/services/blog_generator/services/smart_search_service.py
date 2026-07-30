"""
智能知识源搜索服务 - 根据主题智能路由到不同搜索源
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .search_service import get_search_service
from .arxiv_service import get_arxiv_service
from ..schemas.outputs import SearchRouterOutput
from ..structured_output import parse_structured_output, repair_legacy_json

logger = logging.getLogger(__name__)

# 专业博客网站配置
PROFESSIONAL_BLOGS = {
    'langchain': {
        'site': 'blog.langchain.dev',
        'name': 'LangChain Blog',
        'keywords': ['langchain', 'langgraph', 'lcel', 'langsmith'],
        'quality_weight': 0.85,
    },
    'anthropic': {
        'site': 'anthropic.com',
        'name': 'Anthropic Research',
        'keywords': ['claude', 'anthropic', 'constitutional ai', 'rlhf'],
        'quality_weight': 0.95,
    },
    'openai': {
        'site': 'openai.com',
        'name': 'OpenAI Blog',
        'keywords': ['gpt', 'chatgpt', 'openai', 'dall-e', 'whisper', 'sora'],
        'quality_weight': 0.95,
    },
    'huggingface': {
        'site': 'huggingface.co',
        'name': 'Hugging Face',
        'keywords': ['huggingface', 'transformers', 'diffusers', '开源模型', 'llama', 'mistral'],
        'quality_weight': 0.85,
    },
    'jiqizhixin': {
        'site': 'jiqizhixin.com',
        'name': '机器之心',
        'keywords': ['机器之心', '中文', 'ai资讯'],
        'quality_weight': 0.70,
    },
    'github': {
        'site': 'github.com',
        'name': 'GitHub',
        'keywords': ['github', '开源', 'repo', '仓库', '源码'],
        'quality_weight': 0.75,
    },
    'google_ai': {
        'site': 'blog.google/technology/ai',
        'name': 'Google AI Blog',
        'keywords': ['google', 'gemini', 'bard', 'deepmind', 'tensorflow', 'jax'],
        'quality_weight': 0.90,
    },
    'devto': {
        'site': 'dev.to',
        'name': 'Dev.to',
        'keywords': ['dev.to', '社区', 'tutorial'],
        'quality_weight': 0.70,
    },
    'stackoverflow': {
        'site': 'stackoverflow.com',
        'name': 'Stack Overflow',
        'keywords': ['stackoverflow', '问答', 'debug', '报错', 'error'],
        'quality_weight': 0.75,
    },
    'aws': {
        'site': 'aws.amazon.com/blogs',
        'name': 'AWS Blog',
        'keywords': ['aws', 'lambda', 'sagemaker', 'bedrock', 's3', 'ec2'],
        'quality_weight': 0.80,
    },
    'microsoft': {
        'site': 'devblogs.microsoft.com',
        'name': 'Microsoft DevBlogs',
        'keywords': ['azure', 'microsoft', 'copilot', '.net', 'typescript', 'vscode'],
        'quality_weight': 0.80,
    },
    # ===== 71 号方案新增 AI 权威博客源 =====
    'deepmind': {
        'site': 'deepmind.google',
        'name': 'Google DeepMind',
        'keywords': ['deepmind', 'alphafold', 'alphacode', 'gemma', 'deepmind research'],
        'quality_weight': 0.95,
    },
    'meta_ai': {
        'site': 'ai.meta.com',
        'name': 'Meta AI',
        'keywords': ['meta ai', 'llama', 'llama3', 'codellama', 'meta research', 'fair'],
        'quality_weight': 0.95,
    },
    'mistral': {
        'site': 'mistral.ai',
        'name': 'Mistral AI',
        'keywords': ['mistral', 'mixtral', 'mistral ai', 'pixtral', 'codestral'],
        'quality_weight': 0.90,
    },
    'xai': {
        'site': 'x.ai',
        'name': 'xAI',
        'keywords': ['xai', 'grok', 'x.ai'],
        'quality_weight': 0.85,
    },
    'ms_research': {
        'site': 'microsoft.com/research',
        'name': 'Microsoft Research',
        'keywords': ['microsoft research', 'phi', 'orca', 'autogen', 'semantic kernel'],
        'quality_weight': 0.90,
    },
    # ===== 71 号方案 Phase B: 社区搜索源 =====
    'reddit_ai': {
        'site': 'reddit.com',
        'name': 'Reddit AI',
        'keywords': ['reddit', '社区讨论', 'r/machinelearning', 'r/localllama'],
        'quality_weight': 0.70,
    },
    'hackernews': {
        'site': 'news.ycombinator.com',
        'name': 'Hacker News',
        'keywords': ['hacker news', 'hn', 'ycombinator', 'hackernews'],
        'quality_weight': 0.75,
    },
}

# ===== 71 号方案 Phase C: AI 话题自动增强 =====

# AI 话题关键词（触发自动增强搜索）
AI_TOPIC_KEYWORDS = [
    # 通用 AI 术语
    'ai', '人工智能', 'artificial intelligence', 'machine learning', '机器学习',
    'deep learning', '深度学习', 'neural network', '神经网络',
    # LLM 相关
    'llm', '大模型', '大语言模型', 'large language model', 'foundation model',
    'prompt', 'rag', 'agent', 'fine-tuning', '微调', 'embedding',
    # 具体模型/产品
    'gpt', 'claude', 'gemini', 'llama', 'mistral', 'grok',
    'chatgpt', 'copilot', 'cursor', 'midjourney', 'stable diffusion',
    # AI 应用
    'ai agent', 'ai coding', 'vibe coding', 'ai 编程', 'ai 写作',
    'mcp', 'model context protocol',
]

# AI 话题自动增强的搜索源
AI_BOOST_SOURCES = [
    'anthropic', 'openai', 'google_ai', 'deepmind',
    'meta_ai', 'mistral', 'huggingface',
]

# 全局服务实例
_smart_search_service: Optional['SmartSearchService'] = None


class SmartSearchService:
    """
    智能搜索服务 - 根据主题智能选择搜索源
    """
    
    def __init__(self, llm_client=None):
        """
        初始化智能搜索服务

        Args:
            llm_client: LLM 客户端，用于智能路由
        """
        self.llm = llm_client
        self.max_workers = int(os.environ.get('BLOG_GENERATOR_MAX_WORKERS', '3'))
        # 37.04: 查询重复检测
        from utils.query_deduplicator import QueryDeduplicator
        self.deduplicator = QueryDeduplicator()
        # 71: SourceCurator 源质量评估与健康检查
        from .source_curator import SourceCurator
        self.curator = SourceCurator()
        # 41.02: 源可信度筛选（与 SourceCurator 并列，形成两级过滤管线）
        self._credibility_filter = None
        if os.environ.get('SOURCE_CREDIBILITY_ENABLED', 'false').lower() == 'true' and llm_client:
            from .source_credibility_filter import SourceCredibilityFilter
            self._credibility_filter = SourceCredibilityFilter(llm_client)
            logger.info("源可信度筛选已启用 (41.02)")
    
    def search(self, topic: str, article_type: str = '', max_results_per_source: int = 5) -> Dict[str, Any]:
        """
        智能搜索 - 根据主题选择搜索源并并行执行
        
        Args:
            topic: 搜索主题
            article_type: 文章类型
            max_results_per_source: 每个源的最大结果数
            
        Returns:
            合并后的搜索结果
        """
        logger.info(f"🧠 智能搜索开始: {topic}")

        # 37.04: 查询重复检测
        if self.deduplicator.is_duplicate(topic, agent="smart_search"):
            logger.warning(f"🔁 重复查询跳过: {topic}")
            allowed = self.deduplicator.rollback()
            return {
                'success': True,
                'results': [],
                'summary': '',
                'sources_used': [],
                'error': None,
                'skipped_duplicate': True,
                'rollback_allowed': allowed,
            }
        self.deduplicator.record(topic, agent="smart_search")
        self.deduplicator.reset_rollback_count()

        # 第一步：LLM 判断需要哪些搜索源
        routing_result = self._route_search_sources(topic)
        
        sources = routing_result.get('sources', ['general'])
        arxiv_query = routing_result.get('arxiv_query', topic)
        blog_query = routing_result.get('blog_query', topic)

        # 71 号方案 Phase C：AI 话题自动增强
        if os.environ.get('AI_BOOST_ENABLED', 'true').lower() == 'true':
            sources = self._boost_ai_sources(sources, topic)

        logger.info(f"🧠 搜索源路由结果: {sources}")

        # 71: 健康检查 — 过滤不健康的源
        sources = self.curator.get_healthy_sources(sources)

        # 第二步：并行执行搜索
        all_results = []
        search_tasks = []
        
        # 准备搜索任务
        if 'arxiv' in sources:
            search_tasks.append(('arxiv', arxiv_query))
        
        # 专业博客搜索
        for source in sources:
            if source in PROFESSIONAL_BLOGS:
                search_tasks.append(('blog', source, blog_query))
        
        # 通用搜索（始终包含）
        if 'general' in sources or not search_tasks:
            search_tasks.append(('general', blog_query))

        # Google 搜索（75.02 Serper）
        if 'google' in sources:
            search_tasks.append(('google', blog_query))

        # 搜狗搜索（75.07 腾讯云 SearchPro）
        if 'sogou' in sources:
            search_tasks.append(('sogou', blog_query))
        
        # 并行执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for task in search_tasks:
                if task[0] == 'arxiv':
                    future = executor.submit(self._search_arxiv, task[1], max_results_per_source)
                    futures[future] = 'arxiv'
                elif task[0] == 'blog':
                    future = executor.submit(self._search_blog, task[1], task[2], max_results_per_source)
                    futures[future] = f'blog:{task[1]}'
                elif task[0] == 'general':
                    future = executor.submit(self._search_general, task[1], max_results_per_source)
                    futures[future] = 'general'
                elif task[0] == 'google':
                    future = executor.submit(self._search_google, task[1], max_results_per_source)
                    futures[future] = 'google'
                elif task[0] == 'sogou':
                    future = executor.submit(self._search_sogou, task[1], max_results_per_source)
                    futures[future] = 'sogou'
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    result = future.result()
                    if result.get('success') and result.get('results'):
                        all_results.extend(result['results'])
                        logger.info(f"✅ {source_name} 搜索完成: {len(result['results'])} 条结果")
                        # 71: 记录成功
                        self.curator.record_success(source_name.replace('blog:', ''))
                    elif not result.get('success'):
                        # 71: 记录失败
                        self.curator.record_failure(source_name.replace('blog:', ''))
                except Exception as e:
                    logger.error(f"❌ {source_name} 搜索失败: {e}")
                    # 71: 记录失败
                    self.curator.record_failure(source_name.replace('blog:', ''))
        
        # 第三步：合并去重
        merged_results = self._merge_and_dedupe(all_results)

        # 统一清洗所有搜索结果：HTML 标签 + source 字段
        for item in merged_results:
            if not item.get('source') or item.get('source') == '通用搜索':
                item['source'] = item.get('url', '通用搜索')
            if item.get('title'):
                item['title'] = re.sub(r'<[^>]+>', '', item['title'])
            if item.get('content'):
                item['content'] = re.sub(r'<[^>]+>', '', item['content'])

        # 第四步：41.02 源可信度筛选（LLM 四维评估）
        if self._credibility_filter and merged_results:
            merged_results = self._credibility_filter.curate(
                query=topic, search_results=merged_results,
            )

        logger.info(f"🧠 智能搜索完成: 共 {len(merged_results)} 条结果")
        
        return {
            'success': True,
            'results': merged_results,
            'summary': self._generate_summary(merged_results),
            'sources_used': sources,
            'error': None
        }
    
    def _route_search_sources(self, topic: str) -> Dict[str, Any]:
        """使用 LLM 判断需要哪些搜索源"""
        if not self.llm:
            return self._rule_based_routing(topic)

        from ..prompts import get_prompt_manager
        prompt = get_prompt_manager().render_search_router(topic)

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = parse_structured_output(
                SearchRouterOutput,
                response,
                mode="compat",
                repair=repair_legacy_json,
            ).model_dump(mode="json")

            # 确保 general 始终包含
            if 'general' not in result.get('sources', []):
                result['sources'].append('general')

            return result

        except Exception as e:
            logger.warning(f"LLM 路由失败，使用规则匹配: {e}")
            return self._rule_based_routing(topic)

    def _rule_based_routing(self, topic: str) -> Dict[str, Any]:
        """基于规则的简单路由（LLM 不可用时的备选）"""
        topic_lower = topic.lower()
        sources = ['general']
        
        # 检查是否需要 arXiv
        arxiv_keywords = ['论文', 'paper', '研究', 'research', '算法', 'algorithm', '模型', 'model', 'transformer', 'attention']
        if any(kw in topic_lower for kw in arxiv_keywords):
            sources.append('arxiv')
        
        # 检查专业博客
        for blog_id, config in PROFESSIONAL_BLOGS.items():
            if any(kw in topic_lower for kw in config['keywords']):
                sources.append(blog_id)

        # 75.02: 如果 Serper 可用，自动加入 Google 搜索
        try:
            from .serper_search_service import get_serper_service
            serper = get_serper_service()
            if serper and serper.is_available():
                sources.append('google')
        except Exception:
            pass

        # 75.07: 如果搜狗可用且为中文主题，自动加入搜狗搜索
        try:
            from .sogou_search_service import get_sogou_service
            sogou = get_sogou_service()
            if sogou and sogou.is_available():
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in topic)
                if has_chinese:
                    sources.append('sogou')
        except Exception:
            pass
        
        return {
            'sources': sources,
            'arxiv_query': topic,
            'blog_query': topic
        }

    # ===== 71 号方案 Phase C: AI 话题自动增强 =====

    @staticmethod
    def _is_ai_topic(topic: str) -> bool:
        """检测是否为 AI 相关话题"""
        topic_lower = topic.lower()
        return any(kw in topic_lower for kw in AI_TOPIC_KEYWORDS)

    def _boost_ai_sources(self, sources: List[str], topic: str) -> List[str]:
        """AI 话题自动增强：确保覆盖所有 AI 权威博客源"""
        if not self._is_ai_topic(topic):
            return sources

        boosted = list(sources)
        added = 0
        for src in AI_BOOST_SOURCES:
            if src not in boosted:
                boosted.append(src)
                added += 1

        # AI 话题也加入 arXiv
        if 'arxiv' not in boosted:
            boosted.append('arxiv')
            added += 1

        if added:
            logger.info(f"🚀 AI 话题增强: +{added} 个额外源")
        return boosted

    def _search_arxiv(self, query: str, max_results: int) -> Dict[str, Any]:
        """搜索 arXiv"""
        from utils.rate_limiter import get_global_rate_limiter
        get_global_rate_limiter().wait_sync(domain='search_arxiv')
        arxiv_service = get_arxiv_service()
        if arxiv_service:
            return arxiv_service.search(query, max_results)
        return {'success': False, 'results': [], 'error': 'arXiv 服务不可用'}
    
    def _search_blog(self, blog_id: str, query: str, max_results: int) -> Dict[str, Any]:
        """搜索专业博客（使用 site: 限定）"""
        search_service = get_search_service()
        if not search_service or not search_service.is_available():
            return {'success': False, 'results': [], 'error': '搜索服务不可用'}
        
        blog_config = PROFESSIONAL_BLOGS.get(blog_id)
        if not blog_config:
            return {'success': False, 'results': [], 'error': f'未知博客: {blog_id}'}
        
        # 使用 site: 限定搜索
        site_query = f"{query} site:{blog_config['site']}"
        logger.info(f"📝 专业博客搜索: {site_query}")
        
        result = search_service.search(site_query, max_results)
        
        # 标记来源
        if result.get('results'):
            for item in result['results']:
                item['source'] = blog_config['name']
        
        return result
    
    def _search_general(self, query: str, max_results: int) -> Dict[str, Any]:
        """通用搜索"""
        from utils.rate_limiter import get_global_rate_limiter
        get_global_rate_limiter().wait_sync(domain='search_general')
        search_service = get_search_service()
        if search_service and search_service.is_available():
            result = search_service.search(query, max_results)
            # 标记来源 + 清洗 HTML
            if result.get('results'):
                for item in result['results']:
                    if not item.get('source'):
                        item['source'] = item.get('url', '通用搜索')
                    # 清洗 HTML 标签（如搜索引擎返回的 <em> 高亮）
                    if item.get('title'):
                        item['title'] = re.sub(r'<[^>]+>', '', item['title'])
                    if item.get('content'):
                        item['content'] = re.sub(r'<[^>]+>', '', item['content'])
            return result
        return {'success': False, 'results': [], 'error': '搜索服务不可用'}
    
    def _search_google(self, query: str, max_results: int) -> Dict[str, Any]:
        """Google 搜索（通过 Serper API，75.02）"""
        from utils.rate_limiter import get_global_rate_limiter
        get_global_rate_limiter().wait_sync(domain='search_serper')
        from .serper_search_service import get_serper_service
        serper = get_serper_service()
        if not serper or not serper.is_available():
            return {'success': False, 'results': [], 'error': 'Serper 服务不可用'}
        return serper.search(query, max_results)

    def _search_sogou(self, query: str, max_results: int) -> Dict[str, Any]:
        """搜狗搜索（通过腾讯云 SearchPro API，75.07）"""
        from utils.rate_limiter import get_global_rate_limiter
        get_global_rate_limiter().wait_sync(domain='search_sogou')
        from .sogou_search_service import get_sogou_service
        sogou = get_sogou_service()
        if not sogou or not sogou.is_available():
            return {'success': False, 'results': [], 'error': '搜狗搜索服务不可用'}
        return sogou.search(query, max_results)

    def _merge_and_dedupe(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并去重搜索结果，并按源质量排序"""
        seen_urls = set()
        merged = []

        for item in results:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(item)
            elif not url:
                # 无 URL 的结果也保留（如某些摘要）
                merged.append(item)

        # 71: SourceCurator 按源质量排序
        return self.curator.rank(merged)
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> str:
        """生成搜索结果摘要"""
        if not results:
            return ''
        
        summary_parts = []
        for i, item in enumerate(results, 1):
            source = item.get('source', '未知来源')
            title = item.get('title', '')
            content = item.get('content', '')[:800]
            
            summary_parts.append(f"[{source}] {title}\n{content}")
        
        return '\n\n---\n\n'.join(summary_parts)


def init_smart_search_service(llm_client=None) -> SmartSearchService:
    """初始化智能搜索服务"""
    global _smart_search_service
    _smart_search_service = SmartSearchService(llm_client)
    logger.info("智能知识源搜索服务已初始化")
    return _smart_search_service


def get_smart_search_service() -> Optional[SmartSearchService]:
    """获取智能搜索服务实例"""
    return _smart_search_service
