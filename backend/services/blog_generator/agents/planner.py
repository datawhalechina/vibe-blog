"""
Planner Agent - 大纲规划
"""

import logging
from typing import Dict, Any

from ..prompts import get_prompt_manager
from ..schemas.outputs import PlannerOutlineOutput
from ..structured_output import parse_structured_output, repair_planner_json

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    大纲规划师 - 负责文章结构设计
    """
    
    def __init__(self, llm_client):
        """
        初始化 Planner Agent
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
    
    def generate_outline(
        self,
        topic: str,
        article_type: str,
        target_audience: str,
        audience_adaptation: str = "technical-beginner",
        target_length: str = "medium",
        background_knowledge: str = "",
        key_concepts: list = None,
        on_stream: callable = None,
        target_sections_count: int = None,
        target_images_count: int = None,
        target_code_blocks_count: int = None,
        target_word_count: int = None,
        instructional_analysis: dict = None,
        verbatim_data: list = None,
        distilled_sources: list = None,
        content_gaps: list = None,
        writing_recommendations: dict = None,
        material_by_type: dict = None,
        common_themes: list = None,
        contradictions: list = None
    ) -> Dict[str, Any]:
        """
        生成文章大纲
        
        Args:
            topic: 技术主题
            article_type: 文章类型
            target_audience: 目标受众
            audience_adaptation: 受众适配类型
            target_length: 目标长度 (mini/short/medium/long/custom)
            background_knowledge: 背景知识
            key_concepts: 核心概念列表
            on_stream: 流式回调函数 (delta, accumulated) -> None
            target_sections_count: 目标章节数
            target_images_count: 目标配图数
            target_code_blocks_count: 目标代码块数
            target_word_count: 目标字数
            instructional_analysis: 教学设计分析（新增）
            verbatim_data: 需要原样保留的数据（新增）
            
        Returns:
            大纲字典
        """
        key_concepts = key_concepts or []
        verbatim_data = verbatim_data or []
        
        pm = get_prompt_manager()
        prompt = pm.render_planner(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            audience_adaptation=audience_adaptation,
            target_length=target_length,
            background_knowledge=background_knowledge,
            key_concepts=key_concepts,
            target_sections_count=target_sections_count,
            target_images_count=target_images_count,
            target_code_blocks_count=target_code_blocks_count,
            target_word_count=target_word_count,
            instructional_analysis=instructional_analysis,
            verbatim_data=verbatim_data,
            distilled_sources=distilled_sources or [],
            content_gaps=content_gaps or [],
            writing_recommendations=writing_recommendations or {},
            material_by_type=material_by_type or {},
            common_themes=common_themes or [],
            contradictions=contradictions or []
        )
        
        try:
            # 如果有流式回调且 LLM 支持流式，使用流式生成
            has_stream = hasattr(self.llm, 'chat_stream')
            
            if on_stream and has_stream:
                accumulated = ""
                def on_chunk(delta, acc):
                    nonlocal accumulated
                    accumulated = acc
                    on_stream(delta, acc)
                
                response = self.llm.chat_stream(
                    messages=[{"role": "user", "content": prompt}],
                    on_chunk=on_chunk,
                    response_format={"type": "json_object"}
                )
            else:
                logger.info("使用普通生成大纲")
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
            
            if not response:
                raise ValueError("LLM 返回空响应")
            outline = parse_structured_output(
                PlannerOutlineOutput,
                response,
                mode="compat",
                repair=repair_planner_json,
            ).model_dump(mode="json")
            
            # 为每个章节添加 ID (如果没有) 和新字段默认值
            for i, section in enumerate(outline.get('sections', [])):
                if 'id' not in section:
                    section['id'] = f"section_{i + 1}"
                section.setdefault('core_question', '')
                section.setdefault('assigned_materials', [])
                section.setdefault('subsections', [])

            # 打印素材分配情况
            for section in outline.get('sections', []):
                materials = section.get('assigned_materials', [])
                if materials:
                    logger.info(f"📎 素材分配: [{section.get('title', '')}] ← {len(materials)} 条素材")
                    for m in materials:
                        logger.debug(f"   - source_index={m.get('source_index')}, {m.get('instruction', '')[:60]}")

            return outline
            
        except Exception as e:
            logger.error(f"大纲生成失败: {e}")
            raise

    def run(self, state: Dict[str, Any], on_stream: callable = None) -> Dict[str, Any]:
        """
        执行大纲规划
        
        Args:
            state: 共享状态
            on_stream: 流式回调函数 (delta, accumulated) -> None
            
        Returns:
            更新后的状态
        """
        logger.info(f"开始生成大纲: {state.get('topic', '')}")
        
        try:
            outline = self.generate_outline(
                topic=state.get('topic', ''),
                article_type=state.get('article_type', 'tutorial'),
                target_audience=state.get('target_audience', 'intermediate'),
                audience_adaptation=state.get('audience_adaptation', 'technical-beginner'),
                target_length=state.get('target_length', 'medium'),
                background_knowledge=state.get('background_knowledge', ''),
                key_concepts=state.get('key_concepts', []),
                on_stream=on_stream,
                target_sections_count=state.get('target_sections_count'),
                target_images_count=state.get('target_images_count'),
                target_code_blocks_count=state.get('target_code_blocks_count'),
                target_word_count=state.get('target_word_count'),
                instructional_analysis=state.get('instructional_analysis'),
                verbatim_data=state.get('verbatim_data', []),
                distilled_sources=state.get('distilled_sources', []),
                content_gaps=state.get('content_gaps', []),
                writing_recommendations=state.get('writing_recommendations', {}),
                material_by_type=state.get('material_by_type', {}),
                common_themes=state.get('common_themes', []),
                contradictions=state.get('contradictions', [])
            )
            
            state['outline'] = outline
            
            # 提取信息架构（新增）
            information_architecture = outline.get('information_architecture')
            if information_architecture:
                state['information_architecture'] = information_architecture
                logger.info(f"📐 信息架构: {information_architecture.get('structure_type', 'unknown')}")
            
            logger.info(f"大纲生成完成: {outline.get('title', '')}, {len(outline.get('sections', []))} 个章节")
            
        except Exception as e:
            state['error'] = f"大纲生成失败: {str(e)}"
            logger.error(state['error'])
        
        return state
