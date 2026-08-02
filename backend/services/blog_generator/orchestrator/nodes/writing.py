"""Writing and section-improvement node handlers."""

import logging

from . import is_enabled, resolve_style, validate_layer


logger = logging.getLogger("services.blog_generator.generator")


def _content_word_count(state):
    return sum(
        len(section.get("content", ""))
        for section in state.get("sections", [])
        if section.get("content")
    )


def _log_word_count_diff(agent_name, before, after):
    difference = after - before
    suffix = f"+{difference} 字" if difference >= 0 else f"{difference} 字"
    logger.info(f"📊 [{agent_name}] 字数变化: {before} → {after} ({suffix})")


def writer_node(state, *, writer, layer_validator, memory_storage, configured_style):
    logger.info("=== Step 3: 内容撰写 ===")
    validate_layer(layer_validator, "content", state)
    if memory_storage:
        try:
            memory_injection = memory_storage.format_for_injection(
                state.get("user_id", "default")
            )
            if memory_injection:
                background = state.get("background_knowledge", "")
                state["background_knowledge"] = (
                    f"{background}\n\n{memory_injection}"
                    if background
                    else memory_injection
                )
                logger.info(f"注入用户记忆: {len(memory_injection)} 字符")
        except Exception as error:
            logger.debug(f"用户记忆注入跳过: {error}")

    persona_prompt = resolve_style(state, configured_style).get_persona_prompt()
    if persona_prompt:
        state["_persona_prompt"] = persona_prompt
        logger.info(f"[41.10] 注入人设 Prompt: {persona_prompt[:60]}...")

    before_count = _content_word_count(state)
    result = writer.run(state)
    _log_word_count_diff("Writer", before_count, _content_word_count(result))
    if not result.get("accumulated_knowledge"):
        result["accumulated_knowledge"] = result.get("background_knowledge", "")
    return result


def questioner_node(state, *, questioner):
    logger.info("=== Step 4: 追问检查 ===")
    return questioner.run(state)


def deepen_content_node(
    state,
    *,
    writer,
    parallel_executor,
    tracker,
    task_config_factory,
):
    logger.info("=== Step 4.1: 内容深化 ===")
    before_count = _content_word_count(state)
    state["questioning_count"] = state.get("questioning_count", 0) + 1
    sections_to_deepen = [
        result
        for result in state.get("question_results", [])
        if not result.get("is_detailed_enough", True)
    ]
    total_to_deepen = len(sections_to_deepen)
    if total_to_deepen == 0:
        logger.info("没有需要深化的章节")
        return state

    tasks = []
    for index, result in enumerate(sections_to_deepen, 1):
        section_id = result.get("section_id", "")
        for section in state.get("sections", []):
            if section.get("id") == section_id:
                section_title = section.get("title", section_id)
                tasks.append({
                    "name": f"深化-{section_title}",
                    "fn": writer.enhance_section,
                    "kwargs": {
                        "original_content": section.get("content", ""),
                        "vague_points": result.get("vague_points", []),
                        "section_title": section_title,
                        "progress_info": f"[{index}/{total_to_deepen}]",
                    },
                    "_section_id": section_id,
                })
                break
    results = parallel_executor.run_parallel(
        tasks,
        config=task_config_factory(name="content_deepen", timeout_seconds=120),
    )
    for index, result in enumerate(results):
        if result.success:
            target_id = tasks[index]["_section_id"]
            for section in state.get("sections", []):
                if section.get("id") == target_id:
                    section["content"] = result.result
                    logger.info(f"章节深化完成: {section.get('title', '')}")
                    break
        else:
            logger.error(f"章节深化失败: {result.error}")

    after_count = _content_word_count(state)
    _log_word_count_diff("内容深化", before_count, after_count)
    tracker.log_deepen_snapshot(
        round_num=state.get("questioning_count", 0),
        sections_deepened=total_to_deepen,
        chars_added=after_count - before_count,
    )
    return state


def section_evaluate_node(
    state,
    *,
    questioner,
    tracker,
    configured_style,
):
    style = resolve_style(state, configured_style)
    if not is_enabled(
        "SECTION_EVAL_ENABLED", getattr(style, "enable_thread_check", True)
    ):
        logger.info("段落评估已禁用，跳过")
        state["section_evaluations"] = []
        state["needs_section_improvement"] = False
        return state

    logger.info("=== Step 4.2: 段落多维度评估 ===")
    sections = state.get("sections", [])
    evaluations = []
    needs_improvement = False
    for index, section in enumerate(sections):
        evaluation = questioner.evaluate_section(
            section_content=section.get("content", ""),
            section_title=section.get("title", ""),
            prev_summary=sections[index - 1].get("title", "") if index > 0 else "",
            next_preview=(
                sections[index + 1].get("title", "")
                if index < len(sections) - 1
                else ""
            ),
        )
        evaluation["section_idx"] = index
        evaluations.append(evaluation)
        if evaluation["overall_quality"] < 7.0:
            needs_improvement = True
            logger.info(
                f"  段落 [{section.get('title', '')}] 需改进: "
                f"overall={evaluation['overall_quality']}"
            )
    state["section_evaluations"] = evaluations
    state["needs_section_improvement"] = needs_improvement
    average = sum(
        evaluation["overall_quality"] for evaluation in evaluations
    ) / max(len(evaluations), 1)
    logger.info(f"段落评估完成: 平均分 {average:.1f}, 需改进={needs_improvement}")
    for evaluation in evaluations:
        tracker.log_section_evaluation(
            section_title=sections[evaluation.get("section_idx", 0)].get("title", ""),
            scores=evaluation.get("scores", {}),
            overall=evaluation["overall_quality"],
        )
    return state


def section_improve_node(state, *, writer, tracker):
    logger.info("=== Step 4.3: 段落精准改进 ===")
    evaluations = state.get("section_evaluations", [])
    sections = state.get("sections", [])
    improved_count = 0
    for evaluation in evaluations:
        index = evaluation.get("section_idx", -1)
        if (
            evaluation["overall_quality"] >= 7.0
            or index < 0
            or index >= len(sections)
        ):
            continue
        section = sections[index]
        section["content"] = writer.improve_section(
            original_content=section.get("content", ""),
            critique=evaluation,
            section_title=section.get("title", ""),
        )
        improved_count += 1
    state["section_improve_count"] = state.get("section_improve_count", 0) + 1
    logger.info(
        f"段落改进完成: 改进了 {improved_count} 个段落 "
        f"(第 {state['section_improve_count']} 轮)"
    )
    new_average = sum(
        evaluation["overall_quality"] for evaluation in evaluations
    ) / max(len(evaluations), 1)
    tracker.log_section_improve_snapshot(
        round_num=state["section_improve_count"],
        improved_count=improved_count,
        avg_score_before=state.get("prev_section_avg_score", 0),
        avg_score_after=new_average,
    )
    return state
