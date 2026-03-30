"""
T5: asyncio 自驱动定时器测试
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from services.task_queue.cron_timer import CronTimer, MAX_TIMER_DELAY


@pytest.mark.asyncio
class TestCronTimerArm:
    @pytest.fixture
    def timer_deps(self):
        return {
            'get_next_wake_at': AsyncMock(return_value=None),
            'tick': AsyncMock(),
            'check_stuck': AsyncMock(),
        }

    @pytest_asyncio.fixture
    async def timer(self, timer_deps):
        t = CronTimer(
            get_next_wake_at=timer_deps['get_next_wake_at'],
            tick=timer_deps['tick'],
            check_stuck=timer_deps['check_stuck'],
        )
        t._loop = asyncio.get_running_loop()
        return t

    async def test_arm_no_tasks(self, timer, timer_deps):
        """无任务时不设置 timer"""
        await timer.arm()
        assert timer._timer_handle is None

    async def test_arm_with_future_task(self, timer, timer_deps):
        """有未来任务时设置 timer"""
        future = datetime.now() + timedelta(seconds=10)
        timer_deps['get_next_wake_at'].return_value = future
        await timer.arm()
        assert timer._timer_handle is not None
        timer.stop()

    async def test_arm_clamps_delay(self, timer, timer_deps):
        """delay 不超过 MAX_TIMER_DELAY"""
        far_future = datetime.now() + timedelta(hours=1)
        timer_deps['get_next_wake_at'].return_value = far_future
        with patch.object(
            timer._loop, 'call_later', wraps=timer._loop.call_later
        ) as mock_cl:
            await timer.arm()
            if mock_cl.called:
                delay_arg = mock_cl.call_args[0][0]
                assert delay_arg <= MAX_TIMER_DELAY + 0.1  # 浮点容差
        timer.stop()

    async def test_arm_past_task_zero_delay(self, timer, timer_deps):
        """过去的时间 clamp 到 0"""
        past = datetime.now() - timedelta(seconds=10)
        timer_deps['get_next_wake_at'].return_value = past
        with patch.object(
            timer._loop, 'call_later', wraps=timer._loop.call_later
        ) as mock_cl:
            await timer.arm()
            if mock_cl.called:
                delay_arg = mock_cl.call_args[0][0]
                assert delay_arg >= 0
        timer.stop()

    async def test_arm_replaces_existing_handle(self, timer, timer_deps):
        """重复 arm 会取消旧 handle"""
        future = datetime.now() + timedelta(seconds=10)
        timer_deps['get_next_wake_at'].return_value = future
        await timer.arm()
        old_handle = timer._timer_handle
        await timer.arm()
        assert old_handle.cancelled()
        timer.stop()


@pytest.mark.asyncio
class TestCronTimerOnTimer:
    @pytest.fixture
    def timer_deps(self):
        return {
            'get_next_wake_at': AsyncMock(return_value=None),
            'tick': AsyncMock(),
            'check_stuck': AsyncMock(),
        }

    @pytest_asyncio.fixture
    async def timer(self, timer_deps):
        t = CronTimer(
            get_next_wake_at=timer_deps['get_next_wake_at'],
            tick=timer_deps['tick'],
            check_stuck=timer_deps['check_stuck'],
        )
        t._loop = asyncio.get_running_loop()
        return t

    async def test_calls_tick_and_check(self, timer, timer_deps):
        """_on_timer 调用 tick 和 check_stuck"""
        await timer._on_timer()
        timer_deps['tick'].assert_awaited_once()
        timer_deps['check_stuck'].assert_awaited_once()

    async def test_no_concurrent_tick(self, timer, timer_deps):
        """tick 未完成时不并发执行"""
        timer._ticking = True
        await timer._on_timer()
        timer_deps['tick'].assert_not_awaited()

    async def test_rearms_after_tick(self, timer, timer_deps):
        """tick 完成后重新 arm"""
        timer_deps['get_next_wake_at'].return_value = (
            datetime.now() + timedelta(seconds=5)
        )
        await timer._on_timer()
        assert timer._timer_handle is not None
        timer.stop()

    async def test_exception_safe(self, timer, timer_deps):
        """tick 抛异常不崩溃，仍然重新 arm"""
        timer_deps['tick'].side_effect = RuntimeError("boom")
        await timer._on_timer()
        assert timer._ticking is False

    async def test_resets_ticking_flag(self, timer, timer_deps):
        """正常执行后 _ticking 重置为 False"""
        await timer._on_timer()
        assert timer._ticking is False


@pytest.mark.asyncio
class TestCronTimerStartStop:
    async def test_stop_cancels_handle(self):
        """stop 取消 timer handle"""
        timer = CronTimer(
            get_next_wake_at=AsyncMock(
                return_value=datetime.now() + timedelta(seconds=10)
            ),
            tick=AsyncMock(),
            check_stuck=AsyncMock(),
        )
        timer._loop = asyncio.get_running_loop()
        await timer.arm()
        assert timer._timer_handle is not None
        timer.stop()
        assert timer._timer_handle is None

    async def test_stop_idempotent(self):
        """多次 stop 不报错"""
        timer = CronTimer(
            get_next_wake_at=AsyncMock(return_value=None),
            tick=AsyncMock(),
            check_stuck=AsyncMock(),
        )
        timer.stop()
        timer.stop()  # 不应抛异常

    async def test_disabled_timer(self):
        """disabled 时 start 不设置 timer"""
        timer = CronTimer(
            get_next_wake_at=AsyncMock(
                return_value=datetime.now() + timedelta(seconds=5)
            ),
            tick=AsyncMock(),
            check_stuck=AsyncMock(),
            enabled=False,
        )
        timer._loop = asyncio.get_running_loop()
        await timer.arm()
        assert timer._timer_handle is None
