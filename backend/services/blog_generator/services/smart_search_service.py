"""
智能知识源搜索服务 - 根据主题智能路由到不同搜索源
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .search_service import get_search_service
from .arxiv_service import get_arxiv_service

logger = logging.getLogger(__name__)

# 专业博客网站配置
PROFESSIONAL_BLOGS = {
    'langchain': {
        'site': 'blog.langchain.dev',
        'name': 'LangChain Blog',
        'keywords': ['langchain', 'langgraph', 'lcel', 'langsmith']
    },
    'anthropic': {
        'site': 'anthropic.com',
        'name': 'Anthropic Research',
        'keywords': ['claude', 'anthropic', 'constitutional ai', 'rlhf']
    },
    'openai': {
        'site': 'openai.com',
        'name': 'OpenAI Blog',
        'keywords': ['gpt', 'chatgpt', 'openai', 'dall-e', 'whisper']
    },
    'jiqizhixin': {
        'site': 'jiqizhixin.com',
        'name': '机器之心',
        'keywords': ['机器之心', '中文', 'ai资讯']
    }
}

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
        
        # 第一步：LLM 判断需要哪些搜索源
        routing_result = self._route_search_sources(topic)
        
        sources = routing_result.get('sources', ['general'])
        arxiv_query = routing_result.get('arxiv_query', topic)
        blog_query = routing_result.get('blog_query', topic)
        
        logger.info(f"🧠 搜索源路由结果: {sources}")
        
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
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    result = future.result()
                    if result.get('success') and result.get('results'):
                        all_results.extend(result['results'])
                        logger.info(f"✅ {source_name} 搜索完成: {len(result['results'])} 条结果")
                except Exception as e:
                    logger.error(f"❌ {source_name} 搜索失败: {e}")
        
        # 第三步：合并去重
        merged_results = self._merge_and_dedupe(all_results)
        
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
            # 无 LLM 时使用简单规则匹配
            return self._rule_based_routing(topic)
        
        from ..prompts import get_prompt_manager
        prompt = get_prompt_manager().render_search_router(topic)

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
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
        
        return {
            'sources': sources,
            'arxiv_query': topic,
            'blog_query': topic
        }
    
    def _search_arxiv(self, query: str, max_results: int) -> Dict[str, Any]:
        """搜索 arXiv"""
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
        search_service = get_search_service()
        if search_service and search_service.is_available():
            result = search_service.search(query, max_results)
            # 标记来源
            if result.get('results'):
                for item in result['results']:
                    if not item.get('source'):
                        item['source'] = '通用搜索'
            return result
        return {'success': False, 'results': [], 'error': '搜索服务不可用'}
    
    def _merge_and_dedupe(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并去重搜索结果"""
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
        
        return merged
    
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
