"""
MemoryStorage — 按用户隔离的 JSON 文件持久化记忆存储（102.03）

借鉴 DeerFlow memory.json 存储 + mtime 缓存 + 原子写入模式，
适配 VibeBlog 多用户博客生成场景。
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def create_empty_memory(user_id: str) -> dict:
    """创建空的博客记忆结构"""
    now = datetime.now(timezone.utc).isoformat()
    empty_field = {"summary": "", "updatedAt": ""}
    return {
        "version": "1.0",
        "userId": user_id,
        "lastUpdated": now,
        "writingProfile": {
            "preferredStyle": dict(empty_field),
            "preferredLength": dict(empty_field),
            "preferredAudience": dict(empty_field),
            "preferredImageStyle": dict(empty_field),
        },
        "topicHistory": {
            "recentTopics": dict(empty_field),
            "topicClusters": dict(empty_field),
            "avoidTopics": dict(empty_field),
        },
        "qualityPreferences": {
            "revisionPatterns": dict(empty_field),
            "feedbackHistory": dict(empty_field),
        },
        "facts": [],
    }


class MemoryStorage:
    """
    记忆存储层 — 按用户隔离的 JSON 文件存储

    特性：
    - 每个用户一个 JSON 文件（{user_id}.json）
    - mtime 缓存避免重复读取
    - 原子写入（temp + rename）防止数据损坏
    - 事实管理（添加/删除/按类别查询）
    """

    def __init__(self, storage_path: str = "data/memory/"):
        self._base_path = Path(storage_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, dict] = {}
        self._mtimes: Dict[str, float] = {}

    def _user_file(self, user_id: str) -> Path:
        safe_id = user_id.replace("/", "_").replace("..", "_")
        return self._base_path / f"{safe_id}.json"

    def load(self, user_id: str) -> dict:
        """加载用户记忆（带 mtime 缓存）"""
        file_path = self._user_file(user_id)
        try:
            current_mtime = file_path.stat().st_mtime if file_path.exists() else None
        except OSError:
            current_mtime = None

        cached_mtime = self._mtimes.get(user_id)
        if user_id in self._cache and cached_mtime == current_mtime:
            return self._cache[user_id]

        if not file_path.exists():
            memory = create_empty_memory(user_id)
            self._cache[user_id] = memory
            return memory

        try:
            with open(file_path, encoding="utf-8") as f:
                memory = json.load(f)
            self._cache[user_id] = memory
            self._mtimes[user_id] = current_mtime
            return memory
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"记忆文件读取失败 [{user_id}]: {e}")
            return create_empty_memory(user_id)

    def save(self, user_id: str, memory_data: dict) -> bool:
        """原子写入用户记忆（102.07 统一使用 atomic_write）"""
        file_path = self._user_file(user_id)
        try:
            from utils.atomic_write import atomic_write
            memory_data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
            atomic_write(str(file_path), json.dumps(memory_data, indent=2, ensure_ascii=False))
            self._cache[user_id] = memory_data
            self._mtimes[user_id] = file_path.stat().st_mtime
            return True
        except OSError as e:
            logger.error(f"记忆文件写入失败 [{user_id}]: {e}")
            return False

    def add_fact(
        self,
        user_id: str,
        content: str,
        category: str = "preference",
        confidence: float = 0.9,
        source: str = "",
        max_facts: int = 200,
    ) -> Optional[str]:
        """添加一条事实到用户记忆"""
        memory = self.load(user_id)
        fact_id = f"fact_{uuid.uuid4().hex[:8]}"
        fact = {
            "id": fact_id,
            "content": content,
            "category": category,
            "confidence": confidence,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "source": source,
        }
        memory["facts"].append(fact)

        # 超过上限时移除最旧的低置信度事实
        if len(memory["facts"]) > max_facts:
            memory["facts"].sort(key=lambda f: f.get("confidence", 0))
            memory["facts"] = memory["facts"][-max_facts:]

        self.save(user_id, memory)
        return fact_id

    def remove_fact(self, user_id: str, fact_id: str) -> bool:
        """删除一条事实"""
        memory = self.load(user_id)
        original_len = len(memory["facts"])
        memory["facts"] = [f for f in memory["facts"] if f["id"] != fact_id]
        if len(memory["facts"]) < original_len:
            self.save(user_id, memory)
            return True
        return False

    def get_facts_by_category(self, user_id: str, category: str) -> List[dict]:
        """按类别查询事实"""
        memory = self.load(user_id)
        return [f for f in memory["facts"] if f.get("category") == category]

    def update_profile_field(
        self, user_id: str, section: str, field: str, summary: str
    ) -> bool:
        """更新记忆 profile 字段"""
        memory = self.load(user_id)
        if section not in memory:
            return False
        if field not in memory[section]:
            return False
        memory[section][field] = {
            "summary": summary,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        return self.save(user_id, memory)

    def format_for_injection(self, user_id: str) -> str:
        """格式化记忆为系统提示词注入片段"""
        memory = self.load(user_id)

        parts = []

        # Writing Profile
        wp = memory.get("writingProfile", {})
        profile_lines = []
        for key, label in [
            ("preferredStyle", "写作风格"),
            ("preferredLength", "文章长度"),
            ("preferredAudience", "目标受众"),
            ("preferredImageStyle", "配图风格"),
        ]:
            summary = wp.get(key, {}).get("summary", "")
            if summary:
                profile_lines.append(f"- {label}: {summary}")
        if profile_lines:
            parts.append("用户写作偏好:\n" + "\n".join(profile_lines))

        # Topic History
        th = memory.get("topicHistory", {})
        topic_lines = []
        for key, label in [
            ("recentTopics", "近期主题"),
            ("topicClusters", "核心领域"),
            ("avoidTopics", "已写主题"),
        ]:
            summary = th.get(key, {}).get("summary", "")
            if summary:
                topic_lines.append(f"- {label}: {summary}")
        if topic_lines:
            parts.append("主题历史:\n" + "\n".join(topic_lines))

        # Key Facts
        facts = memory.get("facts", [])
        if facts:
            top_facts = sorted(facts, key=lambda f: f.get("confidence", 0), reverse=True)[:10]
            fact_lines = [f"- [{f['category']}] {f['content']}" for f in top_facts]
            parts.append("关键事实:\n" + "\n".join(fact_lines))

        if not parts:
            return ""

        return "<user-memory>\n" + "\n\n".join(parts) + "\n</user-memory>"

    def exists(self, user_id: str) -> bool:
        """检查用户记忆文件是否存在"""
        return self._user_file(user_id).exists()

    def delete(self, user_id: str) -> bool:
        """删除用户记忆"""
        file_path = self._user_file(user_id)
        self._cache.pop(user_id, None)
        self._mtimes.pop(user_id, None)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
