"""
全局限流器 — 单例模式，支持按域（domain）配置独立速率

灵感来源：GPT-Researcher GlobalRateLimiter
适配改造：同步/异步双模式 + 多域隔离 + 指标暴露

域列表：
- 'llm': LLM API 调用限流
- 'search_serper': Serper Google 搜索 API 限流
- 'search_sogou': 搜狗搜索 API 限流
- 'search_general': 通用搜索限流
- 'search_arxiv': arXiv API 限流
"""
import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitMetrics:
    """限流指标"""
    total_waits: int = 0
    total_wait_seconds: float = 0.0
    last_wait_time: float = 0.0


@dataclass
class DomainConfig:
    """单个域的限流配置"""
    min_interval: float = 1.0
    last_request_time: float = 0.0
    metrics: RateLimitMetrics = field(default_factory=RateLimitMetrics)


class GlobalRateLimiter:
    """
    全局限流器单例。

    支持按域（domain）配置独立速率，同时提供同步和异步两种等待模式。
    """

    _instance: ClassVar[Optional['GlobalRateLimiter']] = None
    _sync_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls):
        with cls._sync_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._domains: Dict[str, DomainConfig] = {}
        self._domain_locks: Dict[str, threading.Lock] = {}
        self._async_locks: Dict[str, asyncio.Lock] = {}
        self._initialized = True
        self._load_env_config()

    def _load_env_config(self):
        """从环境变量加载默认配置"""
        defaults = {
            'llm': float(os.environ.get('LLM_MIN_REQUEST_INTERVAL', '1.0')),
            'search_serper': float(os.environ.get('SERPER_RATE_LIMIT_INTERVAL', '1.0')),
            'search_sogou': float(os.environ.get('SOGOU_RATE_LIMIT_INTERVAL', '0.5')),
            'search_general': float(os.environ.get('SEARCH_RATE_LIMIT_INTERVAL', '0.5')),
            'search_arxiv': float(os.environ.get('ARXIV_RATE_LIMIT_INTERVAL', '3.0')),
        }
        for domain, interval in defaults.items():
            self.configure(domain, interval)

    def configure(self, domain: str, min_interval: float):
        """配置指定域的最小请求间隔"""
        if domain not in self._domains:
            self._domains[domain] = DomainConfig(min_interval=min_interval)
            self._domain_locks[domain] = threading.Lock()
        else:
            self._domains[domain].min_interval = min_interval

    def wait_sync(self, domain: str = 'llm'):
        """同步限流等待（用于 ThreadPoolExecutor 等同步上下文）"""
        config = self._domains.get(domain)
        if not config or config.min_interval <= 0:
            return
        lock = self._domain_locks[domain]
        with lock:
            now = time.monotonic()
            elapsed = now - config.last_request_time
            if elapsed < config.min_interval:
                sleep_time = config.min_interval - elapsed
                time.sleep(sleep_time)
                config.metrics.total_waits += 1
                config.metrics.total_wait_seconds += sleep_time
                config.metrics.last_wait_time = sleep_time
            config.last_request_time = time.monotonic()

    async def wait_async(self, domain: str = 'llm'):
        """异步限流等待（用于 asyncio 上下文）"""
        config = self._domains.get(domain)
        if not config or config.min_interval <= 0:
            return
        if domain not in self._async_locks:
            self._async_locks[domain] = asyncio.Lock()
        lock = self._async_locks[domain]
        async with lock:
            now = time.monotonic()
            elapsed = now - config.last_request_time
            if elapsed < config.min_interval:
                sleep_time = config.min_interval - elapsed
                await asyncio.sleep(sleep_time)
                config.metrics.total_waits += 1
                config.metrics.total_wait_seconds += sleep_time
                config.metrics.last_wait_time = sleep_time
            config.last_request_time = time.monotonic()

    def get_metrics(self, domain: str = None) -> Dict:
        """获取限流指标（供 41.08 成本追踪使用）"""
        if domain:
            cfg = self._domains.get(domain)
            if cfg:
                return {
                    'domain': domain,
                    'min_interval': cfg.min_interval,
                    **cfg.metrics.__dict__,
                }
            return {}
        return {
            d: {
                'min_interval': c.min_interval,
                **c.metrics.__dict__,
            }
            for d, c in self._domains.items()
        }

    def reset(self, domain: str = None):
        """重置状态（测试用）"""
        if domain:
            cfg = self._domains.get(domain)
            if cfg:
                cfg.last_request_time = 0.0
                cfg.metrics = RateLimitMetrics()
        else:
            for cfg in self._domains.values():
                cfg.last_request_time = 0.0
                cfg.metrics = RateLimitMetrics()

    @classmethod
    def _reset_singleton(cls):
        """完全重置单例（仅测试用）"""
        with cls._sync_lock:
            cls._instance = None


# 模块级工厂函数
_global_rate_limiter: Optional[GlobalRateLimiter] = None


def get_global_rate_limiter() -> GlobalRateLimiter:
    """获取全局限流器单例"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = GlobalRateLimiter()
    return _global_rate_limiter
