"""
Researcher Agent - 素材收集
"""

import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts.prompt_manager import get_prompt_manager

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
        
        return unique_results[:max_results]
    
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
        
        pm = get_prompt_manager()
        prompt = pm.render_researcher(
            topic=topic,
            search_depth=search_depth,
            target_audience=target_audience,
            search_results=search_results[:10]
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 提取 JSON（处理 markdown 代码块）
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            
            # 尝试解析 JSON
            result = json.loads(json_str)
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
            
            return {
                "background_knowledge": result.get("background_knowledge", ""),
                "key_concepts": key_concepts,
                "top_references": result.get("top_references", [])
            }
            
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
        
        logger.info(f"开始收集素材: {topic}, 文档知识: {len(document_knowledge)} 条")
        
        # 1. 执行网络搜索（保持原有逻辑）
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
            logger.info("使用原有搜索模式（无文档上传）")
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
        state['reference_links'] = [
            r.get('url', r) if isinstance(r, dict) else r
            for r in summary.get('top_references', summary.get('web_references', []))
        ]
        
        stats = state['knowledge_source_stats']
        logger.info(f"素材收集完成: 文档知识 {stats['document_count']} 条, "
                    f"网络搜索 {stats['web_count']} 条, 核心概念 {len(state['key_concepts'])} 个")
        
        return state
