"""
缓存工具模块 - 用于缓存 API 调用结果

使用 diskcache 实现本地文件缓存，无需外部服务。

环境变量配置：
- RESEARCHER_CACHE_ENABLED: 'true' 或 'false'，默认 'true'
- CACHE_TTL_HOURS: 缓存过期时间（小时），默认 24
"""

import json
import hashlib
import os
from pathlib import Path
from typing import Any, Optional
import logging

from infrastructure.paths import RuntimePaths

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器 - 基于 diskcache 的本地文件缓存"""

    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径，默认使用 var/cache
            ttl_hours: 缓存过期时间（小时），默认 24 小时
        """
        try:
            import diskcache

            if cache_dir is None:
                project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
                cache_dir = os.environ.get("CACHE_DIR") or RuntimePaths.from_env(
                    project_root=project_root
                ).cache

            self.cache_dir = Path(cache_dir)
            self.ttl_seconds = ttl_hours * 3600

            # 初始化 diskcache
            self.cache = diskcache.Cache(str(self.cache_dir))

            logger.info(f"💾 缓存管理器初始化: {self.cache_dir}, TTL={ttl_hours}h")

        except ImportError:
            logger.warning("diskcache 未安装，缓存功能将被禁用。请运行: pip install diskcache")
            self.cache = None

    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """
        生成缓存键

        Args:
            prefix: 缓存键前缀（如 'search', 'researcher'）
            **kwargs: 用于生成缓存键的参数

        Returns:
            缓存键（MD5 哈希）
        """
        # 将参数排序后序列化
        sorted_params = json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
        hash_key = hashlib.md5(sorted_params.encode('utf-8')).hexdigest()
        return f"{prefix}_{hash_key}"

    def get(self, prefix: str, **kwargs) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            prefix: 缓存键前缀
            **kwargs: 查询参数

        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        if self.cache is None:
            return None

        cache_key = self._get_cache_key(prefix, **kwargs)

        try:
            value = self.cache.get(cache_key)
            if value is not None:
                logger.info(f"✅ 命中缓存: {cache_key}")
            return value
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None

    def set(self, prefix: str, data: Any, **kwargs) -> None:
        """
        设置缓存数据

        Args:
            prefix: 缓存键前缀
            data: 要缓存的数据
            **kwargs: 查询参数
        """
        if self.cache is None:
            return

        cache_key = self._get_cache_key(prefix, **kwargs)

        try:
            # diskcache 的 set 方法：set(key, value, expire=None)
            # expire 参数单位是秒
            self.cache.set(cache_key, data, expire=self.ttl_seconds)
            logger.info(f"💾 缓存已保存: {cache_key}")
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

    def clear(self, prefix: Optional[str] = None) -> int:
        """
        清除缓存

        Args:
            prefix: 如果指定，只清除该前缀的缓存；否则清除所有缓存

        Returns:
            清除的缓存数量
        """
        if self.cache is None:
            return 0

        try:
            if prefix:
                # 清除特定前缀的缓存
                count = 0
                for key in list(self.cache.iterkeys()):
                    if key.startswith(prefix):
                        self.cache.delete(key)
                        count += 1
                logger.info(f"🗑️ 已清除 {count} 个 {prefix} 缓存")
                return count
            else:
                # 清除所有缓存
                count = len(self.cache)
                self.cache.clear()
                logger.info(f"🗑️ 已清除所有缓存 ({count} 个)")
                return count
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")
            return 0

    def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        if self.cache is None:
            return {
                'backend': 'diskcache',
                'status': 'disabled',
                'error': 'diskcache not installed'
            }

        try:
            return {
                'backend': 'diskcache',
                'total_keys': len(self.cache),
                'cache_dir': str(self.cache_dir),
                'size_mb': round(self.cache.volume() / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.warning(f"获取缓存统计信息失败: {e}")
            return {
                'backend': 'diskcache',
                'error': str(e)
            }

    def close(self):
        """关闭缓存连接"""
        if self.cache is not None:
            try:
                self.cache.close()
            except Exception as e:
                logger.warning(f"关闭缓存失败: {e}")


# 全局缓存管理器实例
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        ttl_hours = int(os.environ.get('CACHE_TTL_HOURS', 24))
        _cache_manager = CacheManager(ttl_hours=ttl_hours)
    return _cache_manager


def init_cache_manager(cache_dir: str = None, ttl_hours: int = 24) -> CacheManager:
    """
    初始化全局缓存管理器

    Args:
        cache_dir: 缓存目录路径
        ttl_hours: 缓存过期时间（小时）

    Returns:
        缓存管理器实例
    """
    global _cache_manager
    _cache_manager = CacheManager(cache_dir=cache_dir, ttl_hours=ttl_hours)
    return _cache_manager
