"""
发布流水线：质检 → 发布 → 通知
"""
import logging

from .models import BlogTask

logger = logging.getLogger(__name__)


class PublishPipeline:
    """生成完成后的流水线"""

    async def execute(self, task: BlogTask, blog_result: dict) -> dict:
        # Stage 1: 质量检查
        if not task.publish.skip_quality_check:
            quality = self._quality_check(blog_result)
            if not quality['passed']:
                logger.warning(
                    f"[Pipeline] 质检不通过: {quality['issues']}"
                )
                return {
                    'status': 'quality_check_failed',
                    'issues': quality['issues'],
                }

        # Stage 2: 发布
        publish_result = {'status': 'skipped'}
        if task.publish.auto_publish and task.publish.platform:
            publish_result = await self._publish(
                task.publish.platform, blog_result
            )

        # Stage 3: 通知
        if task.publish.notify_on_complete:
            await self._notify(task, blog_result, publish_result)

        return publish_result

    def _quality_check(self, result: dict) -> dict:
        issues = []
        wc = result.get('word_count', 0)
        if wc < 500:
            issues.append(f"字数过少: {wc}")
        if result.get('image_count', 0) == 0:
            issues.append("缺少配图")
        return {'passed': len(issues) == 0, 'issues': issues}

    async def _publish(self, platform: str, result: dict) -> dict:
        if platform == 'wechat':
            logger.info("[Pipeline] 发布到微信公众号 (TODO)")
            return {'status': 'todo', 'platform': 'wechat'}
        elif platform == 'github-pages':
            logger.info("[Pipeline] 发布到 GitHub Pages (TODO)")
            return {'status': 'todo', 'platform': 'github-pages'}
        return {'status': 'unsupported', 'platform': platform}

    async def _notify(self, task, result, publish_result):
        logger.info(f"[Pipeline] 通知: {task.name} 已完成")
