"""
SearchCoordinator Agent - 搜索协调器
负责管理多轮搜索、检测知识空白、执行细化搜索
"""

import json
import logging
from typing import Dict, Any, List, Optional

from ..prompts import get_prompt_manager
from ..schemas.state import get_max_search_count

logger = logging.getLogger(__name__)


class SearchCoordinator:
    """
    搜索协调器 - 管理多轮搜索
    
    职责：
    1. 管理搜索次数和配额
    2. 检测知识空白
    3. 构造细化查询
    4. 整合多轮搜索结果
    """
    
    def __init__(self, llm_client, search_service):
        """
        初始化搜索协调器
        
        Args:
            llm_client: LLM 客户端
            search_service: 搜索服务
        """
        self.llm = llm_client
        self.search_service = search_service
    
    def can_search(self, state: Dict[str, Any]) -> bool:
        """判断是否还能继续搜索"""
        current = state.get('search_count', 0)
        max_count = state.get('max_search_count', 5)
        return current < max_count
    
    def detect_knowledge_gaps(
        self,
        content: str,
        existing_knowledge: str,
        context: str = "",
        topic: str = ""
    ) -> List[Dict[str, Any]]:
        """
        检测知识空白
        
        Args:
            content: 当前内容
            existing_knowledge: 已有背景知识
            context: 上下文信息
            topic: 技术主题
            
        Returns:
            知识空白列表，每项包含:
            - gap_type: "missing_data" | "vague_concept" | "no_example"
            - description: 空白描述
            - suggested_query: 建议的搜索查询
        """
        pm = get_prompt_manager()
        prompt = pm.render_knowledge_gap_detector(
            content=content,
            existing_knowledge=existing_knowledge,
            context=context,
            topic=topic
        )
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            gaps = result.get('gaps', [])
            
            logger.info(f"检测到 {len(gaps)} 个知识空白")
            for gap in gaps:
                logger.debug(f"  - [{gap.get('gap_type')}] {gap.get('description')}")
            
            return gaps
            
        except Exception as e:
            logger.error(f"知识空白检测失败: {e}")
            return []
    
    def refine_search(
        self,
        gaps: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行细化搜索
        
        Args:
            gaps: 知识空白列表
            state: 当前状态
            
        Returns:
            搜索结果字典，包含:
            - success: 是否成功
            - results: 搜索结果列表
            - new_knowledge: 新增知识摘要
        """
        if not self.can_search(state):
            logger.warning("已达到最大搜索次数，无法继续搜索")
            return {
                "success": False,
                "reason": "已达到最大搜索次数",
                "results": []
            }
        
        if not gaps:
            logger.info("没有知识空白需要补充")
            return {
                "success": True,
                "results": [],
                "new_knowledge": ""
            }
        
        all_results = []
        queries_used = []
        gaps_addressed = []
        
        # 每轮最多处理2个空白点，避免搜索过多
        for gap in gaps[:2]:
            query = gap.get('suggested_query', '')
            if not query:
                continue
            
            logger.info(f"执行细化搜索: {query}")
            queries_used.append(query)
            gaps_addressed.append(gap.get('description', ''))
            
            try:
                result = self.search_service.search(query, max_results=3)
                if result.get('success'):
                    all_results.extend(result.get('results', []))
            except Exception as e:
                logger.error(f"搜索失败 [{query}]: {e}")
        
        # 更新搜索计数
        current_count = state.get('search_count', 0)
        state['search_count'] = current_count + 1
        
        # 记录搜索历史
        search_history = state.get('search_history', [])
        search_history.append({
            'round': current_count + 1,
            'queries': queries_used,
            'results_count': len(all_results),
            'gaps_addressed': gaps_addressed
        })
        state['search_history'] = search_history
        
        # 去重搜索结果
        unique_results = self._deduplicate_results(all_results)
        
        # 生成新知识摘要
        new_knowledge = self._summarize_results(unique_results, gaps)
        
        # 累积知识
        accumulated = state.get('accumulated_knowledge', '')
        if new_knowledge:
            state['accumulated_knowledge'] = accumulated + "\n\n" + new_knowledge if accumulated else new_knowledge
        
        logger.info(f"细化搜索完成: 第 {current_count + 1} 轮, 获取 {len(unique_results)} 条结果")
        
        return {
            "success": True,
            "results": unique_results,
            "new_knowledge": new_knowledge
        }
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重搜索结果"""
        seen_urls = set()
        unique = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(result)
        
        return unique
    
    def _summarize_results(
        self,
        results: List[Dict],
        gaps: List[Dict]
    ) -> str:
        """
        将搜索结果摘要为知识文本
        
        Args:
            results: 搜索结果列表
            gaps: 原始知识空白
            
        Returns:
            知识摘要文本
        """
        if not results:
            return ""
        
        # 使用模板渲染 prompt
        pm = get_prompt_manager()
        prompt = pm.render_search_summarizer(gaps=gaps, results=results)
        
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            return response.strip()
        except Exception as e:
            logger.error(f"知识摘要生成失败: {e}")
            # 降级：直接拼接结果内容
            return "\n".join([r.get('content', '')[:200] for r in results[:3]])
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行知识空白检查和细化搜索
        
        Args:
            state: 共享状态
            
        Returns:
            更新后的状态
        """
        if state.get('error'):
            logger.error(f"前置步骤失败，跳过知识检查: {state.get('error')}")
            return state
        
        sections = state.get('sections', [])
        if not sections:
            logger.warning("没有章节内容，跳过知识检查")
            state['knowledge_gaps'] = []
            return state
        
        # 合并所有章节内容
        all_content = "\n\n".join([
            f"## {s.get('title', '')}\n{s.get('content', '')}"
            for s in sections
        ])
        
        existing_knowledge = state.get('accumulated_knowledge', '') or state.get('background_knowledge', '')
        topic = state.get('topic', '')
        
        logger.info(f"开始知识空白检查 (当前搜索次数: {state.get('search_count', 0)}/{state.get('max_search_count', 5)})")
        
        # 检测知识空白
        gaps = self.detect_knowledge_gaps(
            content=all_content,
            existing_knowledge=existing_knowledge,
            context=f"文章主题: {topic}",
            topic=topic
        )
        
        state['knowledge_gaps'] = gaps
        
        return state
