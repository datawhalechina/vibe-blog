"""
MemoryExtractQueue — 去抖记忆提取队列

按 user_id 去重，去抖窗口后批量调用 MemoryExtractor。
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractContext:
    user_id: str
    messages: list[dict]
    source: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryExtractQueue:
    """去抖记忆提取队列"""

    def __init__(self, debounce_seconds: int = 10):
        self._queue: list[ExtractContext] = []
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._processing = False
        self._debounce = debounce_seconds
        self._extractor = None  # 延迟注入

    def set_extractor(self, extractor) -> None:
        self._extractor = extractor

    def add(self, user_id: str, messages: list[dict], source: str = "") -> None:
        ctx = ExtractContext(user_id=user_id, messages=messages, source=source)
        with self._lock:
            # 按 user_id 去重（新消息覆盖旧消息）
            self._queue = [c for c in self._queue if c.user_id != user_id]
            self._queue.append(ctx)
            self._reset_timer()
        logger.info(f"记忆提取已入队: user={user_id}, queue_size={len(self._queue)}")

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self._debounce, self._process)
        self._timer.daemon = True
        self._timer.start()

    def _process(self) -> None:
        if not self._extractor:
            logger.warning("MemoryExtractQueue: extractor 未设置")
            return
        with self._lock:
            if self._processing or not self._queue:
                return
            self._processing = True
            batch = self._queue.copy()
            self._queue.clear()
            self._timer = None

        try:
            for ctx in batch:
                try:
                    self._extractor.extract_and_update(
                        ctx.user_id, ctx.messages, ctx.source
                    )
                except Exception as e:
                    logger.error(f"记忆提取失败 [{ctx.user_id}]: {e}")
                if len(batch) > 1:
                    time.sleep(0.5)
        finally:
            with self._lock:
                self._processing = False

    def flush(self) -> None:
        """立即处理队列（用于测试和优雅关闭）"""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
        self._process()

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)
