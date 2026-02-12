"""
Researcher Agent - 素材收集
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..services.smart_search_service import get_smart_search_service, init_smart_search_service
from ..utils.cache_utils import get_cache_manager

logger = logging.getLogger(__name__)


class ResearcherAgent:
    """
    主题素材收集师 - 负责联网搜索收集背景资料
    支持文档知识融合（一期）
    """
    
    def __init__(self, llm_client, search_service=None, knowledge_service=None):
        """
        初始化 Researcher Agent

        Args:
            llm_client: LLM 客户端
            search_service: 搜索服务 (可选，如果不提供则跳过搜索)
            knowledge_service: 知识服务 (可选，用于文档知识融合)
        """
        self.llm = llm_client
        self.search_service = search_service
        self.knowledge_service = knowledge_service

        # 初始化缓存管理器
        self.cache_enabled = os.environ.get('RESEARCHER_CACHE_ENABLED', 'true').lower() == 'true'
        if self.cache_enabled:
            self.cache = get_cache_manager()
            logger.info("💾 Researcher 缓存已启用")
        else:
            self.cache = None

        # 检查是否启用智能搜索
        self.smart_search_enabled = os.environ.get('SMART_SEARCH_ENABLED', 'false').lower() == 'true'
        if self.smart_search_enabled:
            # 初始化智能搜索服务
            smart_service = get_smart_search_service()
            if not smart_service:
                init_smart_search_service(llm_client)
            logger.info("🧠 智能知识源搜索已启用")
    
    def generate_search_queries(self, topic: str, target_audience: str) -> List[str]:
        """
        生成搜索查询
        
        Args:
            topic: 技术主题
            target_audience: 目标受众
            
        Returns:
            搜索查询列表
        """
        # 默认搜索策略
        default_queries = [
            f"{topic} 教程 tutorial",
            f"{topic} 最佳实践 best practices",
            f"{topic} 常见问题 FAQ",
        ]
        
        if not self.llm:
            return default_queries
        
        try:
            pm = get_prompt_manager()
            prompt = pm.render_search_query(
                topic=topic,
                target_audience=target_audience
            )
            
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            queries = json.loads(response)
            if isinstance(queries, list):
                return queries
            return default_queries
            
        except Exception as e:
            logger.warning(f"生成搜索查询失败: {e}，使用默认查询")
            return default_queries
    
    def search(self, topic: str, target_audience: str, max_results: int = 10) -> List[Dict]:
        """
        执行搜索

        Args:
            topic: 技术主题
            target_audience: 目标受众
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        # 尝试从缓存获取
        if self.cache:
            cached_result = self.cache.get(
                'search',
                topic=topic,
                target_audience=target_audience,
                max_results=max_results
            )
            if cached_result is not None:
                return cached_result

        if not self.search_service:
            logger.warning("搜索服务未配置，跳过搜索")
            return []

        queries = self.generate_search_queries(topic, target_audience)
        all_results = []

        for query in queries:
            try:
                result = self.search_service.search(query, max_results=max_results // len(queries))
                if result.get('success') and result.get('results'):
                    all_results.extend(result['results'])
            except Exception as e:
                logger.error(f"搜索失败 [{query}]: {e}")

        # 去重
        seen_urls = set()
        unique_results = []
        for item in all_results:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(item)

        final_results = unique_results[:max_results]

        # 保存到缓存
        if self.cache:
            self.cache.set(
                'search',
                final_results,
                topic=topic,
                target_audience=target_audience,
                max_results=max_results
            )

        return final_results
    
    def _smart_search(self, topic: str, target_audience: str, max_results: int = 15) -> List[Dict]:
        """
        使用智能搜索服务（LLM 路由 + 多源并行）

        Args:
            topic: 技术主题
            target_audience: 目标受众
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        # 尝试从缓存获取
        if self.cache:
            cached_result = self.cache.get(
                'smart_search',
                topic=topic,
                target_audience=target_audience,
                max_results=max_results
            )
            if cached_result is not None:
                return cached_result

        smart_service = get_smart_search_service()
        if not smart_service:
            logger.warning("智能搜索服务未初始化，回退到普通搜索")
            return self.search(topic, target_audience, max_results)

        try:
            result = smart_service.search(
                topic=topic,
                article_type=target_audience,
                max_results_per_source=5
            )

            if result.get('success'):
                sources_used = result.get('sources_used', [])
                logger.info(f"🧠 智能搜索完成，使用搜索源: {sources_used}")
                search_results = result.get('results', [])[:max_results]

                # 保存到缓存
                if self.cache:
                    self.cache.set(
                        'smart_search',
                        search_results,
                        topic=topic,
                        target_audience=target_audience,
                        max_results=max_results
                    )

                return search_results
            else:
                logger.warning(f"智能搜索失败: {result.get('error')}，回退到普通搜索")
                return self.search(topic, target_audience, max_results)

        except Exception as e:
            logger.error(f"智能搜索异常: {e}，回退到普通搜索")
            return self.search(topic, target_audience, max_results)
    
    def summarize(
        self,
        topic: str,
        search_results: List[Dict],
        target_audience: str,
        search_depth: str = "medium"
    ) -> Dict[str, Any]:
        """
        整理搜索结果，生成背景知识摘要

        Args:
            topic: 技术主题
            search_results: 搜索结果
            target_audience: 目标受众
            search_depth: 搜索深度

        Returns:
            整理后的结果
        """
        if not search_results:
            return {
                "background_knowledge": f"关于 {topic} 的背景知识将在后续章节中详细介绍。",
                "key_concepts": [],
                "top_references": []
            }

        # 尝试从缓存获取（基于 topic 和搜索结果的 URL 列表）
        if self.cache:
            result_urls = [r.get('url', '') for r in search_results[:10]]
            cached_result = self.cache.get(
                'summarize',
                topic=topic,
                target_audience=target_audience,
                search_depth=search_depth,
                result_urls=result_urls
            )
            if cached_result is not None:
                return cached_result

        pm = get_prompt_manager()
        prompt = pm.render_researcher(
            topic=topic,
            search_depth=search_depth,
            target_audience=target_audience,
            search_results=search_results[:10]
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # 提取 JSON（处理 markdown 代码块）
            json_str = response.strip()
            if '```json' in json_str:
                start = json_str.find('```json') + 7
                end = json_str.find('```', start)
                json_str = json_str[start:end].strip() if end != -1 else json_str[start:].strip()
            elif '```' in json_str:
                start = json_str.find('```') + 3
                end = json_str.find('```', start)
                json_str = json_str[start:end].strip() if end != -1 else json_str[start:].strip()

            # 尝试解析 JSON
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = json.loads(json_str, strict=False)
            key_concepts = result.get("key_concepts", [])

            # 调试：打印实际返回内容
            logger.info(f"LLM 返回 key_concepts 类型: {type(key_concepts)}, 值: {key_concepts}")

            # 如果 key_concepts 为空但有其他可能的字段名
            if not key_concepts:
                # 尝试其他可能的字段名
                for alt_key in ['keyConcepts', 'concepts', 'core_concepts', 'keywords']:
                    if result.get(alt_key):
                        key_concepts = result.get(alt_key)
                        logger.info(f"使用备选字段 {alt_key}: {key_concepts}")
                        break

            if key_concepts:
                logger.info(f"核心概念: {[c.get('name', c) if isinstance(c, dict) else c for c in key_concepts[:5]]}")

            # 解析 Instructional Design 分析（新增）
            instructional_analysis = result.get("instructional_analysis", {})
            if instructional_analysis:
                learning_objectives = instructional_analysis.get("learning_objectives", [])
                verbatim_data = instructional_analysis.get("verbatim_data", [])
                content_type = instructional_analysis.get("content_type", "tutorial")
                logger.info(f"📚 教学设计分析: 学习目标 {len(learning_objectives)} 个, "
                           f"Verbatim 数据 {len(verbatim_data)} 项, 内容类型: {content_type}")

            summary_result = {
                "background_knowledge": result.get("background_knowledge", ""),
                "key_concepts": key_concepts,
                "top_references": result.get("top_references", []),
                "instructional_analysis": instructional_analysis  # 新增
            }

            # 保存到缓存
            if self.cache:
                result_urls = [r.get('url', '') for r in search_results[:10]]
                self.cache.set(
                    'summarize',
                    summary_result,
                    topic=topic,
                    target_audience=target_audience,
                    search_depth=search_depth,
                    result_urls=result_urls
                )

            return summary_result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 响应内容: {response[:500] if response else 'None'}")
        except Exception as e:
            logger.error(f"整理搜索结果失败: {e}")

        # 返回简单摘要
        return {
            "background_knowledge": '\n'.join([
                item.get('content', '')[:200] for item in search_results[:3]
            ]),
            "key_concepts": [],
            "top_references": [
                {"title": item.get('title', ''), "url": item.get('url', '')}
                    for item in search_results[:5]
                ]
            }
    
    def distill(self, topic: str, search_results: List[Dict]) -> Dict[str, Any]:
        """
        深度提炼搜索结果（类 OpenDraft Scribe）

        Args:
            topic: 技术主题
            search_results: 原始搜索结果

        Returns:
            提炼后的结构化素材
        """
        empty_result = {
            "sources": [],
            "common_themes": [],
            "contradictions": [],
            "material_by_type": {"concepts": [], "cases": [], "data": [], "comparisons": []}
        }
        if not search_results:
            return empty_result

        # 尝试从缓存获取
        if self.cache:
            result_urls = [r.get('url', '') for r in search_results[:15]]
            cached_result = self.cache.get(
                'distill',
                topic=topic,
                result_urls=result_urls
            )
            if cached_result is not None:
                return cached_result

        pm = get_prompt_manager()
        prompt = pm.render_distill_sources(
            topic=topic,
            search_results=search_results[:15]
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # 提取 JSON
            json_str = response.strip()
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()

            result = json.loads(json_str)

            # 确保必要字段存在
            result.setdefault('sources', [])
            result.setdefault('common_themes', [])
            result.setdefault('contradictions', [])
            result.setdefault('material_by_type',
                              {"concepts": [], "cases": [], "data": [], "comparisons": []})

            logger.info(f"🔬 深度提炼完成: {len(result['sources'])} 条素材, "
                        f"{len(result['common_themes'])} 个共同主题, "
                        f"{len(result['contradictions'])} 个矛盾点")

            # 保存到缓存
            if self.cache:
                result_urls = [r.get('url', '') for r in search_results[:15]]
                self.cache.set(
                    'distill',
                    result,
                    topic=topic,
                    result_urls=result_urls
                )

            return result

        except Exception as e:
            logger.error(f"深度提炼失败: {e}")
            return empty_result

    def analyze_gaps(self, topic: str, article_type: str, distilled: Dict[str, Any]) -> Dict[str, Any]:
        """
        缺口分析（类 OpenDraft Signal）

        Args:
            topic: 技术主题
            article_type: 文章类型
            distilled: distill() 的输出

        Returns:
            缺口分析结果
        """
        empty_result = {
            "content_gaps": [],
            "unique_angles": [],
            "writing_recommendations": {}
        }
        if not distilled or not distilled.get('sources'):
            return empty_result

        # 尝试从缓存获取
        if self.cache:
            cached_result = self.cache.get(
                'analyze_gaps',
                topic=topic,
                article_type=article_type,
                themes_count=len(distilled.get('common_themes', []))
            )
            if cached_result is not None:
                return cached_result

        pm = get_prompt_manager()
        prompt = pm.render_analyze_gaps(
            topic=topic,
            article_type=article_type,
            common_themes=distilled.get('common_themes', []),
            material_by_type=distilled.get('material_by_type', {}),
            contradictions=distilled.get('contradictions', [])
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # 提取 JSON
            json_str = response.strip()
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()

            result = json.loads(json_str)

            # 确保必要字段存在
            result.setdefault('content_gaps', [])
            result.setdefault('unique_angles', [])
            result.setdefault('writing_recommendations', {})

            logger.info(f"🔍 缺口分析完成: {len(result['content_gaps'])} 个缺口, "
                        f"{len(result['unique_angles'])} 个独特角度")

            # 保存到缓存
            if self.cache:
                self.cache.set(
                    'analyze_gaps',
                    result,
                    topic=topic,
                    article_type=article_type,
                    themes_count=len(distilled.get('common_themes', []))
                )

            return result

        except Exception as e:
            logger.error(f"缺口分析失败: {e}")
            return empty_result

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行素材收集

        支持两种模式：
        1. 无文档上传 → 原有流程（仅网络搜索）
        2. 有文档上传 → 知识融合流程（文档 + 网络搜索）

        Args:
            state: 共享状态

        Returns:
            更新后的状态
        """
        topic = state.get('topic', '')
        target_audience = state.get('target_audience', 'intermediate')
        
        # 获取文档知识（如果有上传文档）
        document_knowledge = state.get('document_knowledge', [])
        has_document = bool(document_knowledge)
        
        logger.info(f"🔍 开始收集素材: {topic}")
        
        # 展示文档知识（标题 + 预览内容分开）
        for doc in document_knowledge[:3]:
            file_name = doc.get('file_name', '未知文档')
            content = doc.get('content', '')
            # 标题行
            logger.info(f"📄 文档: {file_name} ({len(content)} 字)")
            # 预览内容（前1000字，作为单独的日志）
            preview = content[:1000] + '...' if len(content) > 1000 else content
            logger.info(f"__DOC_PREVIEW__{preview}__END_PREVIEW__")
        
        # 1. 执行网络搜索
        if self.smart_search_enabled:
            # 使用智能搜索（LLM 路由 + 多源并行）
            logger.info(f"🧠 启动智能知识源搜索...")
            search_results = self._smart_search(topic, target_audience)
        else:
            # 使用普通搜索
            logger.info(f"🌐 启动网络搜索...")
            search_results = self.search(topic, target_audience)
        
        # 2. 知识融合分支
        if self.knowledge_service and has_document:
            # ✅ 有文档 → 走知识融合逻辑
            logger.info("使用知识融合模式")
            
            # 将文档知识转换为 KnowledgeItem
            doc_items = self.knowledge_service.prepare_document_knowledge(
                [{'filename': d.get('file_name', ''), 'markdown_content': d.get('content', '')} 
                 for d in document_knowledge]
            )
            
            # 将搜索结果转换为 KnowledgeItem
            web_items = self.knowledge_service.convert_search_results(search_results)
            
            # 融合知识
            merged_knowledge = self.knowledge_service.get_merged_knowledge(
                document_knowledge=doc_items,
                web_knowledge=web_items
            )
            
            # 整理为 Prompt 可用格式
            summary = self.knowledge_service.summarize_for_prompt(merged_knowledge)
            
            # 记录知识来源统计
            state['knowledge_source_stats'] = {
                'document_count': len([k for k in merged_knowledge if k.source_type == 'document']),
                'web_count': len([k for k in merged_knowledge if k.source_type == 'web_search']),
                'total_items': len(merged_knowledge)
            }
            state['document_references'] = summary.get('document_references', [])
            
        else:
            # ✅ 无文档 → 完全走原有逻辑，零改动
            logger.info("📋 使用原有搜索模式（无文档上传）")
            logger.info(f"📋 将使用网络搜索结果生成博客内容")
            summary = self.summarize(
                topic=topic,
                search_results=search_results,
                target_audience=target_audience
            )
            state['knowledge_source_stats'] = {
                'document_count': 0,
                'web_count': len(search_results),
                'total_items': len(search_results)
            }
            state['document_references'] = []
        
        # 3. 更新状态
        state['search_results'] = search_results
        state['background_knowledge'] = summary.get('background_knowledge', '')
        state['key_concepts'] = [
            c.get('name', c) if isinstance(c, dict) else c
            for c in summary.get('key_concepts', [])
        ]
        # 保留完整的引用信息（包含 title 和 url）
        state['reference_links'] = [
            r if isinstance(r, dict) else {'title': '', 'url': r}
            for r in summary.get('top_references', summary.get('web_references', []))
        ]
        
        # 4. 更新 Instructional Design 相关状态（新增）
        instructional_analysis = summary.get('instructional_analysis', {})
        state['instructional_analysis'] = instructional_analysis
        state['learning_objectives'] = instructional_analysis.get('learning_objectives', [])
        state['verbatim_data'] = instructional_analysis.get('verbatim_data', [])

        # 5. 深度提炼 + 缺口分析（52号方案）
        distilled = {}
        gap_analysis = {}
        if search_results:
            logger.info("🔬 开始深度提炼搜索结果...")
            distilled = self.distill(topic, search_results)

            logger.info("🔍 开始缺口分析...")
            article_type = state.get('article_type', 'tutorial')
            gap_analysis = self.analyze_gaps(topic, article_type, distilled)

        state['distilled_sources'] = distilled.get('sources', [])
        state['material_by_type'] = distilled.get('material_by_type', {})
        state['common_themes'] = distilled.get('common_themes', [])
        state['contradictions'] = distilled.get('contradictions', [])
        state['content_gaps'] = gap_analysis.get('content_gaps', [])
        state['unique_angles'] = gap_analysis.get('unique_angles', [])
        state['writing_recommendations'] = gap_analysis.get('writing_recommendations', {})

        stats = state['knowledge_source_stats']
        logger.info(f"✅ 素材收集完成: 文档知识 {stats['document_count']} 条, "
                    f"网络搜索 {stats['web_count']} 条, 核心概念 {len(state['key_concepts'])} 个")
        
        # 打印 Instructional Design 统计
        if instructional_analysis:
            logger.info(f"📚 教学设计: 学习目标 {len(state['learning_objectives'])} 个, "
                       f"Verbatim 数据 {len(state['verbatim_data'])} 项")
        
        # 输出 researcher 阶段结果（用于测试 mock）
        import json
        researcher_output = {
            'background_knowledge': state.get('background_knowledge', ''),
            'key_concepts': state.get('key_concepts', []),
            'reference_links': state.get('reference_links', []),
            'learning_objectives': state.get('learning_objectives', []),
            'verbatim_data': state.get('verbatim_data', []),
            'knowledge_source_stats': state.get('knowledge_source_stats', {}),
            'distilled_sources': state.get('distilled_sources', []),
            'content_gaps': state.get('content_gaps', []),
            'writing_recommendations': state.get('writing_recommendations', {}),
        }
        logger.info(f"__RESEARCHER_OUTPUT_JSON__{json.dumps(researcher_output, ensure_ascii=False)}__END_JSON__")
        
        return state
