"""
asyncio 自驱动定时器

对应 OpenClaw: src/cron/service/timer.ts

核心机制：
1. arm() 找到最近的 next_run_at，设置 call_later
2. 到时间触发 _on_timer()
3. _on_timer() 执行到期任务，然后再次 arm()
4. 形成自驱动循环
"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

MAX_TIMER_DELAY = 60.0          # 最大 60 秒，防止时钟漂移
STUCK_RUN_SECONDS = 2 * 60 * 60  # 2 小时卡死阈值


class CronTimer:
    def __init__(
        self,
        get_next_wake_at: Callable[[], Awaitable[Optional[datetime]]],
        tick: Callable[[], Awaitable[None]],
        check_stuck: Callable[[], Awaitable[None]],
        enabled: bool = True,
    ):
        self._get_next_wake_at = get_next_wake_at
        self._tick = tick
        self._check_stuck = check_stuck
        self._enabled = enabled
        self._timer_handle: Optional[asyncio.TimerHandle] = None
        self._ticking = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self):
        """启动定时器循环"""
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

        if self._enabled:
            self._loop.call_soon(lambda: asyncio.ensure_future(self.arm()))
            logger.info("[CronTimer] 定时器已启动")
        else:
            logger.info("[CronTimer] 定时器已禁用")

    def stop(self):
        """停止定时器"""
        if self._timer_handle:
            self._timer_handle.cancel()
            self._timer_handle = None
        logger.info("[CronTimer] 定时器已停止")

    async def arm(self):
        """设置下一次唤醒 — 对应 OpenClaw armTimer()"""
        if self._timer_handle:
            self._timer_handle.cancel()
            self._timer_handle = None

        if not self._enabled or not self._loop:
            return

        next_at = await self._get_next_wake_at()
        if not next_at:
            logger.debug("[CronTimer] 无待执行任务，不设置定时器")
            return

        now = datetime.now()
        delay = max((next_at - now).total_seconds(), 0)
        clamped_delay = min(delay, MAX_TIMER_DELAY)

        self._timer_handle = self._loop.call_later(
            clamped_delay,
            lambda: asyncio.ensure_future(self._on_timer()),
        )
        logger.debug(
            f"[CronTimer] 定时器已设置: {clamped_delay:.1f}s 后唤醒"
            f" (目标: {next_at.isoformat()})"
        )

    async def _on_timer(self):
        """
        定时器触发 — 对应 OpenClaw onTimer()

        如果上一个 tick 还在跑，重新 arm 一个 60s 的 timer 而不是丢弃。
        对应 OpenClaw timer.ts L161-183 (修复 #12025)
        """
        if self._ticking:
            logger.debug("[CronTimer] 上一个 tick 仍在执行，重新等待")
            if self._loop:
                self._timer_handle = self._loop.call_later(
                    MAX_TIMER_DELAY,
                    lambda: asyncio.ensure_future(self._on_timer()),
                )
            return

        self._ticking = True
        try:
            await self._tick()
            await self._check_stuck()
        except Exception as e:
            logger.error(f"[CronTimer] tick 失败: {e}")
        finally:
            self._ticking = False
            await self.arm()
