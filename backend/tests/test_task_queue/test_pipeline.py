"""
test_pipeline.py — 发布流水线测试 (L1-L6)
"""
import pytest

from services.task_queue.models import (
    BlogTask, BlogGenerationConfig, PublishConfig,
)
from services.task_queue.pipeline import PublishPipeline


def _make_task(auto_publish=False, platform=None,
               skip_quality=False, **kwargs):
    return BlogTask(
        name="pipeline测试",
        generation=BlogGenerationConfig(topic="AI"),
        publish=PublishConfig(
            auto_publish=auto_publish,
            platform=platform,
            skip_quality_check=skip_quality,
        ),
        **kwargs,
    )


class TestQualityCheck:
    """L1-L3: 质量检查"""

    @pytest.mark.asyncio
    async def test_l1_pass(self):
        """L1: 质检通过"""
        pipeline = PublishPipeline()
        task = _make_task()
        result = await pipeline.execute(task, {
            'word_count': 3000, 'image_count': 5,
        })
        assert result['status'] == 'skipped'

    @pytest.mark.asyncio
    async def test_l2_fail_low_words(self):
        """L2: 字数不足质检失败"""
        pipeline = PublishPipeline()
        task = _make_task()
        result = await pipeline.execute(task, {
            'word_count': 100, 'image_count': 5,
        })
        assert result['status'] == 'quality_check_failed'
        assert any('字数' in i for i in result['issues'])

    @pytest.mark.asyncio
    async def test_l3_fail_no_images(self):
        """L3: 无配图质检失败"""
        pipeline = PublishPipeline()
        task = _make_task()
        result = await pipeline.execute(task, {
            'word_count': 3000, 'image_count': 0,
        })
        assert result['status'] == 'quality_check_failed'
        assert any('配图' in i for i in result['issues'])


class TestPublish:
    """L4-L5: 发布"""

    @pytest.mark.asyncio
    async def test_l4_skip_quality(self):
        """L4: 跳过质检"""
        pipeline = PublishPipeline()
        task = _make_task(skip_quality=True)
        result = await pipeline.execute(task, {
            'word_count': 100, 'image_count': 0,
        })
        # 不应该因质检失败
        assert result['status'] == 'skipped'

    @pytest.mark.asyncio
    async def test_l5_auto_publish_wechat(self):
        """L5: 自动发布到微信"""
        pipeline = PublishPipeline()
        task = _make_task(auto_publish=True, platform='wechat',
                          skip_quality=True)
        result = await pipeline.execute(task, {
            'word_count': 3000, 'image_count': 5,
        })
        assert result['platform'] == 'wechat'

    @pytest.mark.asyncio
    async def test_l6_unsupported_platform(self):
        """L6: 不支持的平台"""
        pipeline = PublishPipeline()
        task = _make_task(auto_publish=True, platform='unknown',
                          skip_quality=True)
        result = await pipeline.execute(task, {
            'word_count': 3000, 'image_count': 5,
        })
        assert result['status'] == 'unsupported'
