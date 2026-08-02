"""Review, consistency, and revision node handlers."""

import logging

from . import is_enabled, resolve_style
from .writing import _content_word_count, _log_word_count_diff


logger = logging.getLogger("services.blog_generator.generator")


def reviewer_node(state, *, reviewer, tracker, configured_style):
    logger.info("=== Step 7: 质量审核 ===")
    style = resolve_style(state, configured_style)
    revision_count = state.get("revision_count", 0)
    if revision_count >= style.max_revision_rounds:
        logger.info(
            f"[Reviewer] 已达最大修订轮数 ({style.max_revision_rounds})，跳过 R2 审核"
        )
        state["review_approved"] = True
        return state

    state = reviewer.run(state)
    consistency_issues = state.get("thread_issues", []) + state.get(
        "voice_issues", []
    )
    if consistency_issues:
        state["review_issues"] = state.get("review_issues", []) + consistency_issues
        logger.info(f"[Reviewer] 合并一致性检查问题: {len(consistency_issues)} 条")
    tracker.log_review_score(
        score=state.get("review_score", 0),
        round_num=state.get("revision_count", 0),
        summary=(
            f"issues={len(state.get('review_issues', []))} "
            f"approved={state.get('review_approved', False)}"
        ),
    )
    return state


def revision_node(
    state,
    *,
    writer,
    parallel_executor,
    configured_style,
    task_config_factory,
):
    logger.info("=== Step 7.1: 修订 ===")
    before_count = _content_word_count(state)
    state["revision_count"] = state.get("revision_count", 0) + 1
    review_issues = state.get("review_issues", [])
    if not review_issues:
        logger.info("没有需要修订的问题")
        return state
    if resolve_style(state, configured_style).revision_strategy == "correct_only":
        revision_correct_only(
            state,
            review_issues,
            writer=writer,
            parallel_executor=parallel_executor,
            task_config_factory=task_config_factory,
        )
    else:
        revision_enhance(
            state,
            review_issues,
            writer=writer,
            parallel_executor=parallel_executor,
            task_config_factory=task_config_factory,
        )
    _log_word_count_diff("修订", before_count, _content_word_count(state))
    return state


def revision_correct_only(
    state,
    review_issues,
    *,
    writer,
    parallel_executor,
    task_config_factory,
):
    section_issues = {}
    for issue in review_issues:
        section_issues.setdefault(issue.get("section_id", ""), []).append({
            "severity": issue.get("severity", "medium"),
            "description": issue.get("description", ""),
            "affected_content": issue.get("affected_content", ""),
        })
    tasks = []
    for index, (section_id, issues) in enumerate(section_issues.items(), 1):
        for section in state.get("sections", []):
            if section.get("id") == section_id:
                section_title = section.get("title", section_id)
                tasks.append({
                    "name": f"更正-{section_title}",
                    "fn": writer.correct_section,
                    "kwargs": {
                        "original_content": section.get("content", ""),
                        "issues": issues,
                        "section_title": section_title,
                        "progress_info": f"[{index}/{len(section_issues)}]",
                    },
                    "_section_id": section_id,
                })
                break
    results = parallel_executor.run_parallel(
        tasks,
        config=task_config_factory(name="revision_correct", timeout_seconds=120),
    )
    _apply_revision_results(state, tasks, results, "章节更正失败")


def revision_enhance(
    state,
    review_issues,
    *,
    writer,
    parallel_executor,
    task_config_factory,
):
    tasks = []
    for index, issue in enumerate(review_issues, 1):
        section_id = issue.get("section_id", "")
        for section in state.get("sections", []):
            if section.get("id") == section_id:
                section_title = section.get("title", section_id)
                tasks.append({
                    "name": f"修订-{section_title}",
                    "fn": writer.enhance_section,
                    "kwargs": {
                        "original_content": section.get("content", ""),
                        "vague_points": [{
                            "location": section_title,
                            "issue": issue.get("description", ""),
                            "question": issue.get("suggestion", ""),
                            "suggestion": "根据审核建议修改",
                        }],
                        "section_title": section_title,
                        "progress_info": f"[{index}/{len(review_issues)}]",
                    },
                    "_section_id": section_id,
                })
                break
    results = parallel_executor.run_parallel(
        tasks,
        config=task_config_factory(name="revision_enhance", timeout_seconds=240),
    )
    _apply_revision_results(state, tasks, results, "章节修订失败")


def _apply_revision_results(state, tasks, results, error_prefix):
    for index, result in enumerate(results):
        if result.success:
            target_id = tasks[index]["_section_id"]
            for section in state.get("sections", []):
                if section.get("id") == target_id:
                    section["content"] = result.result
                    break
        else:
            logger.error(f"{error_prefix}: {result.error}")


def cross_section_dedup_node(
    state,
    *,
    getenv,
    deduplicator_factory,
    llm_client,
):
    if getenv("CROSS_SECTION_DEDUP_ENABLED", "false").lower() != "true":
        return state
    sections = state.get("sections", [])
    if len(sections) < 2:
        return state
    logger.info("=== Step 5.5: 跨章节语义去重 ===")
    try:
        deduplicator = deduplicator_factory(llm_client=llm_client)
        state["sections"] = deduplicator.deduplicate(sections)
    except Exception as error:
        logger.warning(f"[Dedup] 异常，跳过去重: {error}")
    return state


def consistency_check_node(
    state,
    *,
    configured_style,
    env_thread_check,
    env_voice_check,
    thread_checker,
    voice_checker,
    parallel_executor,
    task_config_factory,
):
    sections = state.get("sections", [])
    if len(sections) < 2:
        state["thread_issues"] = []
        state["voice_issues"] = []
        return state
    style = resolve_style(state, configured_style)
    thread_enabled = is_enabled(
        env_thread_check, style.enable_thread_check
    )
    voice_enabled = is_enabled(env_voice_check, style.enable_voice_check)
    if not thread_enabled and not voice_enabled:
        state["thread_issues"] = []
        state["voice_issues"] = []
        return state

    logger.info("=== Step 6.5: 一致性检查（叙事 + 语气）===")
    tasks = []
    if thread_enabled:
        tasks.append({"name": "叙事一致性", "fn": thread_checker.run, "args": (state,)})
    if voice_enabled:
        tasks.append({"name": "语气一致性", "fn": voice_checker.run, "args": (state,)})
    results = parallel_executor.run_parallel(
        tasks,
        config=task_config_factory(name="consistency_check", timeout_seconds=120),
    )
    for result in results:
        if not result.success:
            logger.error(f"[ConsistencyCheck] {result.task_name} 异常: {result.error}")
    if not thread_enabled:
        state["thread_issues"] = []
    if not voice_enabled:
        state["voice_issues"] = []
    logger.info(
        f"[ConsistencyCheck] 完成: 叙事问题 {len(state.get('thread_issues', []))}, "
        f"语气问题 {len(state.get('voice_issues', []))}"
    )
    return state
