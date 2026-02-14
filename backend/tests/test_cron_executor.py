"""
T6: 任务执行器 + 结果处理测试
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from services.task_queue.cron_executor import CronExecutor
from services.task_queue.models import (
    CronJob, CronSchedule, CronScheduleKind, CronJobStatus,
    CronJobState, BlogGenerationConfig, PublishConfig,
)


@pytest.fixture
def mock_queue_manager():
    mgr = MagicMock()
    mgr.enqueue = AsyncMock(return_value="task123")
    return mgr


@pytest.fixture
def executor(mock_queue_manager):
    return CronExecutor(mock_queue_manager)


@pytest.fixture
def sample_job():
    return CronJob(
        id="exec01", name="测试任务",
        schedule=CronSchedule(kind=CronScheduleKind.CRON, expr="0 8 * * *"),
        generation=BlogGenerationConfig(topic="AI"),
        timeout_seconds=5,
    )


def _compute_next(schedule, now):
    """测试用的简单 compute_next_run_at"""
    return now + timedelta(hours=24)


@pytest.mark.asyncio
class TestExecute:
    async def test_success(self, executor, sample_job):
        result = await executor.execute(sample_job)
        assert result['status'] == 'ok'
        assert isinstance(result['started_at'], datetime)
        assert isinstance(result['ended_at'], datetime)
        assert result['ended_at'] >= result['started_at']

    async def test_timeout(self, executor, sample_job, mock_queue_manager):
        async def slow_enqueue(task):
            await asyncio.sleep(10)
        mock_queue_manager.enqueue = slow_enqueue
        sample_job.timeout_seconds = 1
        result = await executor.execute(sample_job)
        assert result['status'] == 'error'
        assert '超时' in result['error']

    async def test_exception(self, executor, sample_job, mock_queue_manager):
        mock_queue_manager.enqueue = AsyncMock(
            side_effect=RuntimeError("DB down")
        )
        result = await executor.execute(sample_job)
        assert result['status'] == 'error'
        assert 'DB down' in result['error']

    async def test_creates_blog_task_with_prefix(
        self, executor, sample_job, mock_queue_manager
    ):
        await executor.execute(sample_job)
        mock_queue_manager.enqueue.assert_awaited_once()
        task = mock_queue_manager.enqueue.call_args[0][0]
        assert task.name.startswith("[定时]")

    async def test_creates_blog_task_with_scheduled_tag(
        self, executor, sample_job, mock_queue_manager
    ):
        await executor.execute(sample_job)
        task = mock_queue_manager.enqueue.call_args[0][0]
        assert 'scheduled' in task.tags

    async def test_preserves_generation_config(
        self, executor, sample_job, mock_queue_manager
    ):
        await executor.execute(sample_job)
        task = mock_queue_manager.enqueue.call_args[0][0]
        assert task.generation.topic == "AI"


@pytest.mark.asyncio
class TestApplyResult:
    def test_success_resets_errors(self, executor, sample_job):
        sample_job.state.consecutive_errors = 3
        result = {
            'status': 'ok',
            'started_at': datetime.now(),
            'ended_at': datetime.now(),
        }
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.consecutive_errors == 0
        assert sample_job.state.last_status == CronJobStatus.OK

    def test_error_increments(self, executor, sample_job):
        result = {
            'status': 'error', 'error': 'fail',
            'started_at': datetime.now(), 'ended_at': datetime.now(),
        }
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.consecutive_errors == 1
        assert sample_job.state.last_error == 'fail'
        assert sample_job.state.last_status == CronJobStatus.ERROR

    def test_error_backoff_applied(self, executor, sample_job):
        sample_job.state.consecutive_errors = 2  # 将变为 3
        now = datetime.now()
        result = {
            'status': 'error', 'error': 'fail',
            'started_at': now, 'ended_at': now,
        }
        executor.apply_result(sample_job, result, _compute_next)
        # 第 3 次失败，退避 300s
        assert sample_job.state.next_run_at >= now + timedelta(seconds=300)

    def test_clears_running_at(self, executor, sample_job):
        sample_job.state.running_at = datetime.now()
        result = {
            'status': 'ok',
            'started_at': datetime.now(), 'ended_at': datetime.now(),
        }
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.running_at is None

    def test_records_last_run_at(self, executor, sample_job):
        started = datetime(2025, 3, 1, 8, 0)
        result = {
            'status': 'ok',
            'started_at': started, 'ended_at': datetime(2025, 3, 1, 8, 5),
        }
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.last_run_at == started

    def test_records_duration(self, executor, sample_job):
        started = datetime(2025, 3, 1, 8, 0, 0)
        ended = datetime(2025, 3, 1, 8, 0, 5)
        result = {'status': 'ok', 'started_at': started, 'ended_at': ended}
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.last_duration_ms == 5000

    def test_success_computes_next_run(self, executor, sample_job):
        now = datetime.now()
        result = {'status': 'ok', 'started_at': now, 'ended_at': now}
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.next_run_at is not None

    def test_at_task_disables_after_run(self, executor):
        job = CronJob(
            id="at01", name="一次性",
            schedule=CronSchedule(
                kind=CronScheduleKind.AT, at=datetime(2025, 6, 1)
            ),
            generation=BlogGenerationConfig(topic="test"),
        )
        result = {
            'status': 'ok',
            'started_at': datetime.now(), 'ended_at': datetime.now(),
        }
        should_delete = executor.apply_result(job, result, _compute_next)
        assert job.enabled is False
        assert job.state.next_run_at is None
        assert should_delete is False

    def test_at_task_delete_after_run(self, executor):
        job = CronJob(
            id="at02", name="一次性删除",
            schedule=CronSchedule(
                kind=CronScheduleKind.AT, at=datetime(2025, 6, 1)
            ),
            generation=BlogGenerationConfig(topic="test"),
            delete_after_run=True,
        )
        result = {
            'status': 'ok',
            'started_at': datetime.now(), 'ended_at': datetime.now(),
        }
        should_delete = executor.apply_result(job, result, _compute_next)
        assert should_delete is True

    def test_at_task_error_no_delete(self, executor):
        """AT 任务失败时不删除"""
        job = CronJob(
            id="at03", name="一次性失败",
            schedule=CronSchedule(
                kind=CronScheduleKind.AT, at=datetime(2025, 6, 1)
            ),
            generation=BlogGenerationConfig(topic="test"),
            delete_after_run=True,
        )
        result = {
            'status': 'error', 'error': 'fail',
            'started_at': datetime.now(), 'ended_at': datetime.now(),
        }
        should_delete = executor.apply_result(job, result, _compute_next)
        assert should_delete is False
        assert job.enabled is False

    def test_disabled_job_no_next_run(self, executor, sample_job):
        """禁用的 job 不计算 next_run_at"""
        sample_job.enabled = False
        result = {
            'status': 'ok',
            'started_at': datetime.now(), 'ended_at': datetime.now(),
        }
        executor.apply_result(sample_job, result, _compute_next)
        assert sample_job.state.next_run_at is None
