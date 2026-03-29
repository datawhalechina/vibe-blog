"""
task_queue 测试 — 共享 Fixtures

提供：
- FakeBlogGenerator: 模拟博客生成器（可控延迟 + 进度回调）
- tmp_db_path: 临时 SQLite 数据库路径
- task_db: 已初始化的 TaskDB 实例
- queue_manager: 已初始化的 TaskQueueManager 实例
- sample_task: 示例 BlogTask
"""
import asyncio
import os
import sys
import pytest
import pytest_asyncio

# 将 backend 加入 path
_backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, _backend_dir)

from services.task_queue.models import (
    BlogTask, BlogGenerationConfig, TriggerConfig, PublishConfig,
    QueueStatus, TaskPriority, TriggerType,
)
from services.task_queue.db import TaskDB
from services.task_queue.manager import TaskQueueManager


class FakeBlogGenerator:
    """模拟博客生成器 — 可控延迟 + 进度回调"""

    def __init__(self, delay: float = 0.1, fail: bool = False):
        self.delay = delay
        self.fail = fail
        self.call_count = 0
        self.last_config = None

    async def generate(self, config: dict, progress_callback=None) -> dict:
        self.call_count += 1
        self.last_config = config

        if self.fail:
            raise RuntimeError("FakeBlogGenerator: 模拟失败")

        stages = [
            (10, "researcher", "搜索资料中..."),
            (30, "outliner", "生成大纲中..."),
            (60, "writer", "撰写正文中..."),
            (80, "artist", "生成配图中..."),
            (95, "assembler", "组装文章中..."),
        ]
        for progress, stage, detail in stages:
            if progress_callback:
                await progress_callback(progress, stage, detail)
            await asyncio.sleep(self.delay / len(stages))

        return {
            "url": f"/blog/fake-{self.call_count}",
            "word_count": 3000,
            "image_count": 5,
        }


# ── Fixtures ──

@pytest.fixture
def tmp_db_path(tmp_path):
    """临时数据库路径"""
    return str(tmp_path / "test_task_queue.db")


@pytest_asyncio.fixture
async def task_db(tmp_db_path):
    """已初始化的 TaskDB"""
    db = TaskDB(db_path=tmp_db_path)
    await db.init()
    return db


@pytest.fixture
def sample_generation_config():
    return BlogGenerationConfig(topic="测试主题：AI 发展趋势")


@pytest.fixture
def sample_task(sample_generation_config):
    return BlogTask(
        name="测试任务",
        generation=sample_generation_config,
    )


@pytest.fixture
def high_priority_task(sample_generation_config):
    return BlogTask(
        name="高优先级任务",
        generation=sample_generation_config,
        priority=TaskPriority.HIGH,
    )


@pytest.fixture
def fake_generator():
    return FakeBlogGenerator(delay=0.05)


@pytest.fixture
def failing_generator():
    return FakeBlogGenerator(fail=True)


@pytest_asyncio.fixture
async def queue_manager(tmp_db_path, fake_generator):
    """已初始化的 TaskQueueManager（注入 FakeBlogGenerator）"""
    mgr = TaskQueueManager(db_path=tmp_db_path, max_concurrent=2)
    await mgr.init()
    mgr.set_blog_generator(fake_generator)
    return mgr
