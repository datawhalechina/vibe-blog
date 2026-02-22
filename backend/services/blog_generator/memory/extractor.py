"""
MemoryExtractor — LLM 驱动的记忆提取器

从对话中自动提取用户写作偏好、主题兴趣和关键事实，
更新到 MemoryStorage 的结构化记忆中。
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from .storage import MemoryStorage
from .config import BlogMemoryConfig
from .prompts import BLOG_MEMORY_UPDATE_PROMPT, format_conversation

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """LLM 驱动的记忆提取器"""

    def __init__(
        self,
        storage: MemoryStorage,
        config: BlogMemoryConfig,
        llm_service=None,
    ):
        self._storage = storage
        self._config = config
        self._llm_service = llm_service

    def _get_llm(self):
        """获取 LLM 实例（延迟初始化）"""
        if self._llm_service is not None:
            return self._llm_service
        # Fallback: 使用 llm_factory 创建独立实例
        from services.llm_factory import create_llm_client
        import os
        provider = os.getenv("LLM_PROVIDER", "openai")
        model = self._config.model_name or os.getenv("LLM_MODEL", "gpt-4o-mini")
        return create_llm_client(provider=provider, model_name=model, temperature=0.1)

    def extract_and_update(
        self, user_id: str, messages: list[dict], source: str = ""
    ) -> bool:
        """从对话中提取记忆并更新存储

        Args:
            user_id: 用户 ID
            messages: 对话消息列表 [{"role": "user/assistant", "content": "..."}]
            source: 来源标识（如 task_id）

        Returns:
            是否更新成功
        """
        if not self._config.enabled or not self._config.auto_extract_enabled:
            return False
        if not messages:
            return False

        try:
            current_memory = self._storage.load(user_id)
            conversation_text = format_conversation(messages)
            if not conversation_text.strip():
                return False

            prompt = BLOG_MEMORY_UPDATE_PROMPT.format(
                current_memory=json.dumps(current_memory, indent=2, ensure_ascii=False),
                conversation=conversation_text,
            )

            llm = self._get_llm()
            response = llm.invoke(prompt)
            response_text = str(response.content).strip()

            # 移除 markdown 代码块包裹
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )

            update_data = json.loads(response_text)
            updated = self._apply_updates(current_memory, update_data, source)
            return self._storage.save(user_id, updated)

        except json.JSONDecodeError as e:
            logger.warning(f"LLM 记忆提取响应解析失败: {e}")
            return False
        except Exception as e:
            logger.error(f"记忆提取失败 [{user_id}]: {e}")
            return False

    def _apply_updates(
        self, memory: dict, updates: dict, source: str
    ) -> dict:
        """应用 LLM 提取的更新到记忆结构"""
        now = datetime.now(timezone.utc).isoformat()

        # 更新 writingProfile
        wp_updates = updates.get("writingProfile", {})
        for field in ["preferredStyle", "preferredLength",
                       "preferredAudience", "preferredImageStyle"]:
            field_data = wp_updates.get(field, {})
            if field_data.get("shouldUpdate") and field_data.get("summary"):
                memory["writingProfile"][field] = {
                    "summary": field_data["summary"],
                    "updatedAt": now,
                }

        # 更新 topicHistory
        th_updates = updates.get("topicHistory", {})
        for field in ["recentTopics", "topicClusters", "avoidTopics"]:
            field_data = th_updates.get(field, {})
            if field_data.get("shouldUpdate") and field_data.get("summary"):
                memory["topicHistory"][field] = {
                    "summary": field_data["summary"],
                    "updatedAt": now,
                }

        # 更新 qualityPreferences
        qp_updates = updates.get("qualityPreferences", {})
        for field in ["revisionPatterns", "feedbackHistory"]:
            field_data = qp_updates.get(field, {})
            if field_data.get("shouldUpdate") and field_data.get("summary"):
                memory["qualityPreferences"][field] = {
                    "summary": field_data["summary"],
                    "updatedAt": now,
                }

        # 添加新事实（置信度门控）
        for fact in updates.get("newFacts", []):
            confidence = fact.get("confidence", 0.5)
            if confidence >= self._config.fact_confidence_threshold:
                memory["facts"].append({
                    "id": f"fact_{uuid.uuid4().hex[:8]}",
                    "content": fact.get("content", ""),
                    "category": fact.get("category", "context"),
                    "confidence": confidence,
                    "createdAt": now,
                    "source": source,
                })

        # 移除过期事实
        to_remove = set(updates.get("factsToRemove", []))
        if to_remove:
            memory["facts"] = [
                f for f in memory["facts"] if f["id"] not in to_remove
            ]

        # 裁剪至上限
        if len(memory["facts"]) > self._config.max_facts:
            memory["facts"].sort(
                key=lambda f: f.get("confidence", 0), reverse=True
            )
            memory["facts"] = memory["facts"][:self._config.max_facts]

        return memory
