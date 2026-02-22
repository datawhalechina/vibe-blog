"""
1003.09 素材整理服务

迁移自 DeepTutor MaterialOrganizerAgent，适配 vibe-blog LLM 调用。
从笔记本记录中提取结构化知识点，含双层降级策略。
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_DESCRIPTION_LENGTH = 10

MAIN_SYSTEM_PROMPT = (
    '你是一位专业的知识整理专家。请从给定的素材中提取关键知识点，'
    '以 JSON 格式返回。每个知识点必须包含 knowledge_point（标题）和 description（详细描述，不少于10字）。'
)

FALLBACK_SYSTEM_PROMPT = (
    '请从以下素材中提取要点，以 JSON 格式返回 {"knowledge_points": [{"knowledge_point": "...", "description": "..."}]}。'
)


class MaterialOrganizerService:
    """素材整理服务 — 从笔记本记录中提取知识点"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def _format_materials(self, records: List[dict]) -> str:
        parts = []
        for i, rec in enumerate(records, 1):
            parts.append(
                f"[素材 {i}]\n"
                f"类型: {rec.get('record_type', 'unknown')}\n"
                f"标题: {rec.get('title', '')}\n"
                f"问题: {rec.get('user_query', '')}\n"
                f"内容: {rec.get('content', '')}\n"
            )
        return "\n".join(parts)

    def _build_user_prompt(self, materials_text: str, user_thoughts: Optional[str] = None) -> str:
        prompt = f"以下是需要整理的素材：\n\n{materials_text}\n\n"
        if user_thoughts:
            prompt += f"用户补充说明：{user_thoughts}\n\n"
        prompt += (
            '请提取关键知识点，以 JSON 格式返回：\n'
            '{"knowledge_points": [{"knowledge_point": "标题", "description": "详细描述"}]}'
        )
        return prompt

    def _validate_points(self, points: List[dict]) -> List[dict]:
        valid = []
        for p in points:
            kp = p.get("knowledge_point", "")
            desc = p.get("description", "")
            if kp and desc and len(desc) >= MIN_DESCRIPTION_LENGTH:
                valid.append({"knowledge_point": kp, "description": desc})
        return valid

    def _parse_response(self, text: str) -> List[dict]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        if isinstance(data, dict):
            return data.get("knowledge_points", [])
        if isinstance(data, list):
            return data
        return []

    def extract_knowledge_points(
        self, records: List[dict], user_thoughts: Optional[str] = None,
    ) -> List[dict]:
        if not records:
            return []

        materials_text = self._format_materials(records)
        user_prompt = self._build_user_prompt(materials_text, user_thoughts)

        try:
            response = self._call_llm(MAIN_SYSTEM_PROMPT, user_prompt)
            raw_points = self._parse_response(response)
            valid = self._validate_points(raw_points)
            if valid:
                return valid
            logger.warning("主提取无有效知识点，触发降级")
        except Exception as e:
            logger.warning("主提取失败: %s，触发降级", e)

        return self._fallback_extract(records, user_thoughts)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        if self.llm_client is None:
            raise RuntimeError("LLM client not configured")
        return self.llm_client.chat(system_prompt, user_prompt)

    def _fallback_extract(
        self, records: List[dict], user_thoughts: Optional[str] = None,
    ) -> List[dict]:
        materials_text = self._format_materials(records)
        user_prompt = self._build_user_prompt(materials_text, user_thoughts)

        try:
            response = self._call_llm(FALLBACK_SYSTEM_PROMPT, user_prompt)
            raw_points = self._parse_response(response)
            valid = self._validate_points(raw_points)
            if valid:
                return valid
        except Exception as e:
            logger.warning("降级提取也失败: %s，返回兜底结果", e)

        # 极端兜底：从记录标题生成知识点
        fallback = []
        for rec in records[:5]:
            title = rec.get("title", "")
            content = rec.get("content", "")
            if title:
                desc = content[:100] if len(content) >= MIN_DESCRIPTION_LENGTH else f"关于{title}的知识要点，来源于素材记录"
                fallback.append({"knowledge_point": title, "description": desc})
        return fallback if fallback else [
            {"knowledge_point": "素材整理", "description": "当前素材集合的综合知识要点整理"}
        ]
