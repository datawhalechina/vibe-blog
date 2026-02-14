"""
搜索源注册中心 — 从 backend/configs/search/search_sources.yaml 加载配置

统一管理所有搜索源（引擎 + 专业博客 + AI 增强 + 搜索策略）。
替代 smart_search_service.py 中的硬编码 PROFESSIONAL_BLOGS / AI_TOPIC_KEYWORDS 等。

来源：95.00 DeepResearch 集成方案
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# 配置文件路径（统一到 backend/configs/search/）
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "search" / "search_sources.yaml"

# 全局单例
_registry: Optional["SearchSourceRegistry"] = None


class SearchSourceRegistry:
    """搜索源注册中心 — 从 YAML 配置加载所有搜索源元数据"""

    def __init__(self, config_path: str = None):
        self._config_path = config_path or str(_DEFAULT_CONFIG_PATH)
        self._raw: Dict[str, Any] = {}
        self._engines: Dict[str, Dict] = {}
        self._blogs: Dict[str, Dict] = {}
        self._ai_boost: Dict[str, Any] = {}
        self._strategies: Dict[str, Dict] = {}
        self._health: Dict[str, Any] = {}
        self._load()

    # ================================================================
    # 加载
    # ================================================================

    def _load(self) -> None:
        """加载并解析 YAML 配置"""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"搜索源配置文件不存在: {self._config_path}，使用空配置")
            self._raw = {}
        except yaml.YAMLError as e:
            logger.error(f"搜索源配置文件解析失败: {e}，使用空配置")
            self._raw = {}

        self._engines = self._raw.get("engines", {})
        self._blogs = self._raw.get("blogs", {})
        self._ai_boost = self._raw.get("ai_boost", {})
        self._strategies = self._raw.get("strategies", {})
        self._health = self._raw.get("health", {})

        # 过滤掉环境变量缺失的引擎
        for eid, ecfg in list(self._engines.items()):
            if not ecfg.get("enabled", True):
                continue
            for env_key in ecfg.get("env_keys", []):
                if not os.environ.get(env_key):
                    ecfg["enabled"] = False
                    logger.info(f"搜索引擎 {eid} 自动禁用: 缺少环境变量 {env_key}")
                    break

        enabled_engines = [k for k, v in self._engines.items() if v.get("enabled")]
        logger.info(
            f"搜索源注册中心已加载: {len(enabled_engines)} 个引擎, "
            f"{len(self._blogs)} 个专业博客"
        )

    def reload(self) -> None:
        """热重载配置（不重启服务）"""
        self._load()
        logger.info("搜索源配置已热重载")

    # ================================================================
    # 引擎查询
    # ================================================================

    def get_engine(self, engine_id: str) -> Optional[Dict]:
        """获取单个引擎配置"""
        cfg = self._engines.get(engine_id)
        if cfg and cfg.get("enabled", True):
            return cfg
        return None

    def get_enabled_engines(self) -> Dict[str, Dict]:
        """获取所有启用的引擎"""
        return {k: v for k, v in self._engines.items() if v.get("enabled", True)}

    def get_engines_by_type(self, engine_type: str) -> Dict[str, Dict]:
        """按类型获取引擎（general / academic / social）"""
        return {
            k: v for k, v in self._engines.items()
            if v.get("enabled", True) and v.get("type") == engine_type
        }

    def engine_has_capability(self, engine_id: str, capability: str) -> bool:
        """检查引擎是否具有某项能力（如 batch_search, images）"""
        cfg = self._engines.get(engine_id, {})
        return capability in cfg.get("capabilities", [])

    # ================================================================
    # 博客查询
    # ================================================================

    def get_blog(self, blog_id: str) -> Optional[Dict]:
        """获取单个博客配置"""
        return self._blogs.get(blog_id)

    def get_all_blogs(self) -> Dict[str, Dict]:
        """获取所有专业博客"""
        return dict(self._blogs)

    def match_blogs_by_topic(self, topic: str) -> List[str]:
        """根据主题关键词匹配相关的博客源 ID"""
        topic_lower = topic.lower()
        matched = []
        for blog_id, blog_cfg in self._blogs.items():
            keywords = blog_cfg.get("keywords", [])
            if any(kw in topic_lower for kw in keywords):
                matched.append(blog_id)
        return matched

    # ================================================================
    # AI 话题增强
    # ================================================================

    def is_ai_boost_enabled(self) -> bool:
        """AI 话题增强是否启用"""
        env_override = os.environ.get("AI_BOOST_ENABLED", "").lower()
        if env_override:
            return env_override == "true"
        return self._ai_boost.get("enabled", True)

    def get_ai_keywords(self) -> List[str]:
        """获取 AI 话题关键词列表"""
        return self._ai_boost.get("keywords", [])

    def get_ai_boost_sources(self) -> List[str]:
        """获取 AI 话题增强的博客源 ID 列表"""
        return self._ai_boost.get("boost_sources", [])

    def get_ai_boost_engines(self) -> List[str]:
        """获取 AI 话题增强的引擎 ID 列表"""
        return self._ai_boost.get("boost_engines", [])

    def is_ai_topic(self, topic: str) -> bool:
        """检测是否为 AI 相关话题"""
        topic_lower = topic.lower()
        return any(kw in topic_lower for kw in self.get_ai_keywords())

    # ================================================================
    # 搜索策略
    # ================================================================

    def get_strategy(self, strategy_name: str = "default") -> Dict[str, Any]:
        """获取搜索策略配置"""
        return self._strategies.get(strategy_name, self._strategies.get("default", {}))

    def get_all_strategies(self) -> Dict[str, Dict]:
        """获取所有搜索策略"""
        return dict(self._strategies)

    # ================================================================
    # 健康检查配置
    # ================================================================

    def get_health_config(self) -> Dict[str, Any]:
        """获取健康检查配置"""
        return dict(self._health)

    # ================================================================
    # 质量权重（供 SourceCurator 使用）
    # ================================================================

    def build_quality_weights(self) -> Dict[str, float]:
        """构建 source_name → quality_weight 映射（合并引擎 + 博客）"""
        weights: Dict[str, float] = {}

        # 引擎权重
        for ecfg in self._engines.values():
            name = ecfg.get("name", "")
            if name:
                weights[name] = ecfg.get("quality_weight", 0.50)

        # 博客权重
        for bcfg in self._blogs.values():
            name = bcfg.get("name", "")
            if name:
                weights[name] = bcfg.get("quality_weight", 0.50)

        # 通用搜索兜底
        default_w = self._health.get("default_weight", 0.50)
        weights.setdefault("通用搜索", default_w)

        return weights

    # ================================================================
    # 路由关键词（供规则路由使用）
    # ================================================================

    def get_engine_routing_keywords(self) -> Dict[str, List[str]]:
        """获取引擎 → 路由关键词映射"""
        result = {}
        for eid, ecfg in self._engines.items():
            kws = ecfg.get("routing_keywords", [])
            if kws:
                result[eid] = kws
        return result


# ================================================================
# 全局实例管理
# ================================================================

def init_search_source_registry(config_path: str = None) -> SearchSourceRegistry:
    """初始化搜索源注册中心"""
    global _registry
    _registry = SearchSourceRegistry(config_path)
    return _registry


def get_search_source_registry() -> SearchSourceRegistry:
    """获取搜索源注册中心（懒初始化）"""
    global _registry
    if _registry is None:
        _registry = SearchSourceRegistry()
    return _registry
