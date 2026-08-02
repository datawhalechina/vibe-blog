"""Module-level routing policies for the generation graph."""

import logging
from functools import partial, update_wrapper
from typing import Callable, Literal

from .nodes import resolve_style


logger = logging.getLogger("services.blog_generator.generator")


class RoutingStyleResolver:
    def __init__(self, configured_style=None):
        self.configured_style = configured_style

    def __call__(self, state):
        return resolve_style(state, self.configured_style)


def bind_style_resolver(handler: Callable, style_resolver):
    return update_wrapper(
        partial(handler, style_resolver=style_resolver),
        handler,
    )


def _should_improve_sections(state) -> Literal["improve", "continue"]:
    if not state.get("needs_section_improvement", False):
        return "continue"

    improve_count = state.get("section_improve_count", 0)
    if improve_count >= 2:
        logger.info("段落改进达到最大轮数(2)，跳过")
        return "continue"

    evaluations = state.get("section_evaluations", [])
    current_average = (
        sum(evaluation["overall_quality"] for evaluation in evaluations)
        / max(len(evaluations), 1)
    )
    previous_average = state.get("prev_section_avg_score", 0)
    if previous_average > 0 and (current_average - previous_average) < 0.3:
        logger.info(
            "段落改进收敛 (%.1f → %.1f)，跳过",
            previous_average,
            current_average,
        )
        return "continue"

    state["prev_section_avg_score"] = current_average
    return "improve"


def _should_deepen(
    state, *, style_resolver
) -> Literal["deepen", "continue"]:
    count = state.get("questioning_count", 0)
    style = style_resolver(state)
    max_rounds = style.max_questioning_rounds

    if count >= max_rounds:
        logger.info("[Deepen] 已达最大轮数 %s/%s，停止深化", count, max_rounds)
        return "continue"

    if not state.get("all_sections_detailed", True):
        logger.info("[Deepen] 第 %s/%s 轮深化", count + 1, max_rounds)
        return "deepen"

    return "continue"


def _should_continue_questioning(
    state, *, style_resolver
) -> Literal["questioner", "section_evaluate"]:
    count = state.get("questioning_count", 0)
    style = style_resolver(state)
    max_rounds = style.max_questioning_rounds
    if count >= max_rounds:
        logger.info(
            "[Deepen] 深化后已达最大轮数 %s/%s，跳过追问",
            count,
            max_rounds,
        )
        return "section_evaluate"
    return "questioner"


def _should_check_knowledge(state) -> Literal["check", "skip"]:
    if state.get("target_length", "medium") == "mini":
        logger.info("[check_knowledge] mini 模式，跳过知识空白检查")
        return "skip"
    return "check"


def _should_revise(
    state, *, style_resolver
) -> Literal["revision", "assemble"]:
    style = style_resolver(state)
    revision_count = state.get("revision_count", 0)

    if revision_count >= style.max_revision_rounds:
        logger.info("已达到最大修订轮数 (%s)，跳过修订", style.max_revision_rounds)
        return "assemble"

    review_issues = state.get("review_issues", [])
    if style.revision_severity_filter == "high_only":
        high_issues = [
            issue for issue in review_issues
            if issue.get("severity") == "high"
        ]
        if high_issues:
            logger.info(
                "[%s] 只处理 %s 个 high 级别问题",
                style.revision_severity_filter,
                len(high_issues),
            )
            state["review_issues"] = high_issues
            return "revision"
        logger.info("[%s] 无 high 级别问题，跳过修订", style.revision_severity_filter)
        return "assemble"

    if not state.get("review_approved", True):
        return "revision"

    logger.info("审核通过或修订完成，进入组装")
    return "assemble"


def _should_refine_search(
    state, *, style_resolver
) -> Literal["search", "continue"]:
    style = style_resolver(state)
    if not style.enable_knowledge_refinement:
        logger.info("知识增强已禁用，跳过")
        return "continue"

    gaps = state.get("knowledge_gaps", [])
    search_count = state.get("search_count", 0)
    max_count = state.get("max_search_count", 5)
    if gaps and search_count < max_count:
        important_gaps = [
            gap for gap in gaps
            if gap.get("gap_type") in {"missing_data", "vague_concept"}
        ]
        if important_gaps:
            logger.info(
                "检测到 %s 个重要知识空白，触发细化搜索",
                len(important_gaps),
            )
            return "search"

    logger.info("无需细化搜索，继续到追问阶段")
    return "continue"
