"""
TopicIdeaAgent - 四阶段选题生成

基于 DeepTutor IdeaGenerationWorkflow 迁移，适配 vibe-blog Agent 模式。
四阶段流水线：提取知识点 → 松筛 → 探索选题方向 → 严筛 → 生成陈述。
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from ..prompts import get_prompt_manager

logger = logging.getLogger(__name__)


class TopicIdeaAgent:
    """
    四阶段选题生成 Agent

    从搜索结果中提取知识点，通过松筛→探索→严筛→陈述四阶段
    生成高质量选题方向，供 PlannerAgent 使用。
    """

    def __init__(self, llm_client, on_stream: Optional[Callable] = None):
        self.llm = llm_client
        self.on_stream = on_stream

    def _call_llm_json(self, prompt: str) -> Optional[dict]:
        """调用 LLM 并解析 JSON 响应"""
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            if not response:
                return None
            return json.loads(response.strip())
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM JSON 解析失败: {e}")
            return None

    def extract_knowledge_points(
        self, topic: str, search_results: List[dict]
    ) -> List[dict]:
        """Step 1: 从搜索结果提取知识点"""
        if not search_results:
            return []

        snippets = "\n".join(
            f"- {r.get('title', '')}: {r.get('snippet', '')}"
            for r in search_results[:20]
        )
        pm = get_prompt_manager()
        prompt = pm.render(
            "blog/topic_idea",
            phase="extract",
            topic=topic,
            snippets=snippets,
        )
        result = self._call_llm_json(prompt)
        if not result:
            return []

        points = result.get("knowledge_points", [])
        # 验证格式
        valid = [
            p for p in points
            if isinstance(p, dict) and "knowledge_point" in p and "description" in p
        ]
        logger.info(f"[TopicIdea] 提取知识点: {len(valid)} 个")
        return valid

    def loose_filter(self, knowledge_points: List[dict]) -> List[dict]:
        """Step 2: 松筛 — 移除明显无研究价值的知识点"""
        if len(knowledge_points) <= 1:
            return knowledge_points

        points_json = json.dumps(knowledge_points, ensure_ascii=False)
        pm = get_prompt_manager()
        prompt = pm.render(
            "blog/topic_idea",
            phase="loose_filter",
            points_json=points_json,
        )
        result = self._call_llm_json(prompt)
        if not result:
            # fallback: 返回原列表
            return knowledge_points

        filtered = result.get("filtered_points", knowledge_points)
        logger.info(
            f"[TopicIdea] 松筛: {len(knowledge_points)} → {len(filtered)}"
        )
        return filtered if filtered else knowledge_points

    def explore_ideas(self, knowledge_point: dict) -> List[str]:
        """Step 3: 为单个知识点生成 5~10 个选题方向"""
        pm = get_prompt_manager()
        prompt = pm.render(
            "blog/topic_idea",
            phase="explore",
            knowledge_point=knowledge_point.get("knowledge_point", ""),
            description=knowledge_point.get("description", ""),
        )
        result = self._call_llm_json(prompt)
        if not result:
            return []

        ideas = result.get("research_ideas", [])
        logger.info(
            f"[TopicIdea] 探索 '{knowledge_point.get('knowledge_point', '')}': "
            f"{len(ideas)} 个方向"
        )
        return ideas[:10]

    def strict_filter(
        self, knowledge_point: dict, ideas: List[str]
    ) -> List[str]:
        """Step 4: 严筛 — 至少保留 1 个、至少淘汰 2 个"""
        if len(ideas) <= 1:
            return ideas

        ideas_json = json.dumps(ideas, ensure_ascii=False)
        pm = get_prompt_manager()
        prompt = pm.render(
            "blog/topic_idea",
            phase="strict_filter",
            knowledge_point=knowledge_point.get("knowledge_point", ""),
            ideas_json=ideas_json,
        )
        result = self._call_llm_json(prompt)
        if not result:
            # fallback: 保留前半
            return ideas[: max(1, len(ideas) // 2)]

        kept = result.get("kept_ideas", [])
        # 硬性约束：至少保留 1 个
        if not kept:
            kept = [ideas[0]]
        logger.info(
            f"[TopicIdea] 严筛 '{knowledge_point.get('knowledge_point', '')}': "
            f"{len(ideas)} → {len(kept)}"
        )
        return kept

    def generate_statement(self, topic: str, ideas: List[dict]) -> str:
        """Step 5: 生成选题陈述 Markdown"""
        if not ideas:
            return ""

        ideas_json = json.dumps(ideas, ensure_ascii=False)
        pm = get_prompt_manager()
        prompt = pm.render(
            "blog/topic_idea",
            phase="statement",
            topic=topic,
            ideas_json=ideas_json,
        )
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
            )
            return response.strip() if response else ""
        except Exception as e:
            logger.warning(f"[TopicIdea] 陈述生成失败: {e}")
            return ""

    def generate_ideas(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """主入口：执行四阶段选题生成"""
        topic = state.get("topic", "")
        search_results = state.get("search_results", [])

        if self.on_stream:
            self.on_stream("[TopicIdea] 开始选题生成...", "")

        # Step 1: 提取知识点
        knowledge_points = self.extract_knowledge_points(topic, search_results)
        if not knowledge_points:
            logger.info("[TopicIdea] 无知识点可提取，跳过选题生成")
            return {
                "knowledge_points": [],
                "topic_ideas": [],
                "topic_statement": None,
            }

        # Step 2: 松筛
        filtered_points = self.loose_filter(knowledge_points)

        # Step 3+4: 对每个知识点探索+严筛
        all_ideas = []
        for point in filtered_points:
            ideas = self.explore_ideas(point)
            if ideas:
                kept = self.strict_filter(point, ideas)
                for idea in kept:
                    all_ideas.append({
                        "idea": idea,
                        "knowledge_point": point["knowledge_point"],
                    })

        # Step 5: 生成陈述
        statement = self.generate_statement(topic, all_ideas) if all_ideas else None

        logger.info(
            f"[TopicIdea] 完成: {len(filtered_points)} 知识点, "
            f"{len(all_ideas)} 选题方向"
        )
        return {
            "knowledge_points": filtered_points,
            "topic_ideas": all_ideas,
            "topic_statement": statement,
        }
