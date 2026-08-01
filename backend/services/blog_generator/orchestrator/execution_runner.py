"""Compiled graph execution entry points."""

import logging
import os
from typing import Any, Callable, Dict

from ..parallel import ParallelTaskExecutor
from ..schemas.state import create_initial_state
from ..style_profile import StyleProfile


logger = logging.getLogger("services.blog_generator.generator")


class GraphExecutionRunner:
    def __init__(self, generator):
        self.generator = generator

    def generate(
        self,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        target_length: str = "medium",
        source_material: str = None,
        on_progress: Callable[[str, str], None] = None,
    ) -> Dict[str, Any]:
        generator = self.generator
        if generator.app is None:
            generator.compile()

        style = StyleProfile.from_target_length(target_length)
        generator.executor = ParallelTaskExecutor(enable_parallel=style.enable_parallel)

        token_tracker = None
        cost_tracker = None
        try:
            if os.environ.get("TOKEN_TRACKING_ENABLED", "true").lower() == "true":
                from utils.token_tracker import TokenTracker

                token_tracker = TokenTracker()
                generator.llm.token_tracker = token_tracker
            if os.environ.get("COST_TRACKING_ENABLED", "false").lower() == "true":
                from utils.cost_tracker import CostTracker

                cost_tracker = CostTracker()
                generator.llm._cost_tracker = cost_tracker
        except Exception:
            pass

        task_log = None
        try:
            if os.environ.get("BLOG_TASK_LOG_ENABLED", "true").lower() == "true":
                from ..utils.task_log import BlogTaskLog

                task_log = BlogTaskLog(
                    topic=topic,
                    article_type=article_type,
                    target_length=target_length,
                )
                generator.task_log = task_log
                generator._task_log_middleware.set_task_log(task_log)
        except Exception:
            pass

        try:
            from utils.tool_manager import BlogToolManager

            tool_manager = BlogToolManager(task_log=task_log)
            if generator.search_service:
                tool_manager.register(
                    "web_search",
                    generator.search_service.search,
                    description="搜索互联网获取背景知识",
                    timeout=30,
                )
            generator.tool_manager = tool_manager
        except Exception:
            pass

        initial_state = create_initial_state(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material,
        )
        logger.info(f"开始生成博客: {topic}")
        logger.info(
            f"  类型: {article_type}, 受众: {target_audience}, 长度: {target_length}"
        )

        config = generator._build_config(initial_state)
        logger.info(f"[RecursionBudget] limit={config['recursion_limit']}")

        try:
            final_state = generator.app.invoke(initial_state, config)
            logger.info("博客生成完成!")

            token_summary = None
            if token_tracker:
                logger.info(token_tracker.format_summary())
                token_summary = token_tracker.get_summary()

            cost_summary = None
            if cost_tracker:
                logger.info(cost_tracker.format_summary())
                cost_summary = cost_tracker.get_summary()

            if task_log:
                task_log.complete(
                    score=final_state.get("review_score", 0),
                    word_count=len(final_state.get("final_markdown", "")),
                    revision_rounds=final_state.get("revision_count", 0),
                )
                if token_summary:
                    task_log.token_summary = token_summary
                try:
                    task_log.save()
                except Exception as save_err:
                    logger.warning(f"任务日志保存失败: {save_err}")
                logger.info(task_log.get_summary())

            result = {
                "success": True,
                "markdown": final_state.get("final_markdown", ""),
                "outline": final_state.get("outline", {}),
                "sections_count": len(final_state.get("sections", [])),
                "images_count": len(final_state.get("images", [])),
                "code_blocks_count": len(final_state.get("code_blocks", [])),
                "review_score": final_state.get("review_score", 0),
                "seo_keywords": final_state.get("seo_keywords", []),
                "social_summary": final_state.get("social_summary", ""),
                "meta_description": final_state.get("meta_description", ""),
                "error": None,
            }
            if token_summary:
                result["token_summary"] = token_summary
            if cost_summary:
                result["cost_summary"] = cost_summary

            derivatives = generator._run_derivative_skills(final_state)
            if derivatives:
                result["derivatives"] = derivatives
            return result
        except Exception as error:
            logger.error(f"博客生成失败: {error}", exc_info=True)
            if task_log:
                task_log.fail(str(error))
                try:
                    task_log.save()
                except Exception:
                    pass
            return {"success": False, "markdown": "", "error": str(error)}

    async def generate_stream(
        self,
        topic: str,
        article_type: str = "tutorial",
        target_audience: str = "intermediate",
        target_length: str = "medium",
        source_material: str = None,
    ):
        generator = self.generator
        if generator.app is None:
            generator.compile()

        initial_state = create_initial_state(
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material,
        )
        config = generator._build_config(initial_state)
        logger.info(f"[RecursionBudget] limit={config['recursion_limit']}")
        for event in generator.app.stream(initial_state, config):
            for node_name, state in event.items():
                yield {"stage": node_name, "state": state}
