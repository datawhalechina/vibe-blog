"""
71 Searcher — SourceCurator 源质量评估与健康检查

功能：
1. rank(results) — 按源质量权重排序
2. 健康检查 — 连续 3 次失败自动禁用，30 分钟后重新检查
3. get_healthy_sources() — 过滤不健康的源
"""
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)

# 冷却时间（秒）：禁用后 30 分钟重新检查
HEALTH_COOLDOWN = 30 * 60
# 连续失败阈值
MAX_CONSECUTIVE_FAILURES = 3


class SourceCurator:
    """搜索源质量评估与健康管理"""

    # 源质量权重：官方博客 > 技术社区 > 通用搜索
    SOURCE_WEIGHTS: Dict[str, float] = {
        # 官方研究博客（最高权重）
        "Anthropic Research": 0.95,
        "OpenAI Blog": 0.95,
        "Google DeepMind": 0.95,
        "Meta AI": 0.95,
        "Google AI Blog": 0.90,
        "Mistral AI": 0.90,
        "Microsoft Research": 0.90,
        # 产品博客
        "LangChain Blog": 0.85,
        "xAI": 0.85,
        "Hugging Face": 0.85,
        "AWS Blog": 0.80,
        "Microsoft DevBlogs": 0.80,
        # 技术社区
        "Hacker News": 0.75,
        "GitHub": 0.75,
        "Stack Overflow": 0.75,
        "Dev.to": 0.70,
        "Reddit AI": 0.70,
        # 中文媒体
        "机器之心": 0.70,
        # 学术
        "arXiv": 0.90,
        # 通用搜索（最低权重）
        "通用搜索": 0.50,
        "Google Search": 0.60,
        "搜狗搜索": 0.55,
    }

    DEFAULT_WEIGHT = 0.50

    def __init__(self):
        # 连续失败计数 {source_id: count}
        self._failure_counts: Dict[str, int] = {}
        # 禁用时间戳 {source_id: timestamp}
        self._disabled_sources: Dict[str, float] = {}

    # ========== 排序 ==========

    def rank(self, results: List[Dict]) -> List[Dict]:
        """按源质量权重排序（降序）"""
        if not results:
            return []
        return sorted(results, key=lambda r: self._get_weight(r), reverse=True)

    def _get_weight(self, result: Dict) -> float:
        """获取单条结果的源质量权重"""
        source_name = result.get("source", "")
        return self.SOURCE_WEIGHTS.get(source_name, self.DEFAULT_WEIGHT)

    # ========== 健康检查 ==========

    def check_health(self, source_id: str) -> bool:
        """检查源是否健康（可用）"""
        if source_id in self._disabled_sources:
            disabled_at = self._disabled_sources[source_id]
            if time.time() - disabled_at >= HEALTH_COOLDOWN:
                # 冷却期已过，重新启用
                logger.info(f"源 {source_id} 冷却期已过，重新启用")
                self.enable_source(source_id)
                return True
            return False
        return True

    def record_failure(self, source_id: str) -> None:
        """记录一次失败"""
        self._failure_counts[source_id] = self._failure_counts.get(source_id, 0) + 1
        count = self._failure_counts[source_id]
        if count >= MAX_CONSECUTIVE_FAILURES:
            self.disable_source(source_id)
            logger.warning(
                f"源 {source_id} 连续 {count} 次失败，已自动禁用"
            )

    def record_success(self, source_id: str) -> None:
        """记录一次成功，重置失败计数"""
        self._failure_counts.pop(source_id, None)

    def disable_source(self, source_id: str) -> None:
        """手动禁用源"""
        self._disabled_sources[source_id] = time.time()
        logger.info(f"源 {source_id} 已禁用")

    def enable_source(self, source_id: str) -> None:
        """手动启用源"""
        self._disabled_sources.pop(source_id, None)
        self._failure_counts.pop(source_id, None)
        logger.info(f"源 {source_id} 已启用")

    def get_healthy_sources(self, source_ids: List[str]) -> List[str]:
        """过滤出健康的源列表"""
        return [s for s in source_ids if self.check_health(s)]
