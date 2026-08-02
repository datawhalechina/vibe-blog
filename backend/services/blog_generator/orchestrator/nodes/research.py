"""Research and planning node handlers."""

import logging

from . import validate_layer

logger = logging.getLogger("services.blog_generator.generator")


def researcher_node(state, *, researcher, layer_validator):
    if state.get("skip_researcher"):
        logger.info("=== Step 1: 素材收集（已跳过） ===")
        empty_defaults = {
            "background_knowledge": "",
            "key_concepts": [],
            "search_results": [],
            "reference_links": [],
            "knowledge_source_stats": {},
            "instructional_analysis": {},
            "learning_objectives": [],
            "verbatim_data": [],
            "distilled_sources": [],
            "material_by_type": {},
            "common_themes": [],
            "contradictions": [],
            "content_gaps": [],
            "unique_angles": [],
            "writing_recommendations": {},
        }
        for key, default in empty_defaults.items():
            if state.get(key) is None:
                state[key] = default
        return state
    logger.info("=== Step 1: 素材收集 ===")
    validate_layer(layer_validator, "research", state)
    return researcher.run(state)


def planner_node(
    state,
    *,
    planner,
    layer_validator,
    on_stream,
    interactive,
    writing_skill_manager,
    llm_client,
    interrupt_fn,
    getenv,
    image_preplanner_factory,
):
    logger.info("=== Step 2: 大纲规划 ===")
    validate_layer(layer_validator, "structure", state)
    result = planner.run(state, on_stream=on_stream)
    outline = result.get("outline") if isinstance(result, dict) else None
    auto_confirm = (
        state.get("target_length") == "mini"
        or getenv("OUTLINE_AUTO_CONFIRM", "false").lower() == "true"
    )

    if outline and interactive and not auto_confirm:
        sections = outline.get("sections", [])
        user_decision = interrupt_fn({
            "type": "confirm_outline",
            "title": outline.get("title", ""),
            "sections": sections,
            "sections_titles": [section.get("title", "") for section in sections],
            "narrative_mode": outline.get("narrative_mode", ""),
            "narrative_flow": outline.get("narrative_flow", {}),
            "sections_narrative_roles": [
                section.get("narrative_role", "") for section in sections
            ],
        })
        if isinstance(user_decision, dict) and user_decision.get("action") == "edit":
            edited_outline = user_decision.get("outline", outline)
            logger.info(f"大纲已被用户修改: {edited_outline.get('title', '')}")
            result["outline"] = edited_outline
            result["sections"] = []
        else:
            logger.info("大纲已被用户确认")
    elif outline and auto_confirm:
        logger.info(
            f"[AutoConfirm] 自动确认大纲 (target_length={state.get('target_length')})"
        )

    if writing_skill_manager:
        try:
            skill = writing_skill_manager.match_skill(
                state.get("topic", ""), state.get("article_type", "")
            )
            if skill:
                result["_writing_skill_prompt"] = (
                    writing_skill_manager.build_system_prompt_section(skill)
                )
                logger.info(f"匹配写作技能: {skill.name}")
        except Exception as error:
            logger.debug(f"写作技能匹配跳过: {error}")

    if getenv("IMAGE_PREPLAN_ENABLED", "false").lower() == "true":
        try:
            preplanner = image_preplanner_factory(llm_client)
            image_plan = preplanner.plan(
                outline=result.get("outline", {}),
                background_knowledge=state.get("background_knowledge", ""),
                article_type=state.get("article_type", "tutorial"),
            )
            result["image_preplan"] = image_plan
            logger.info(f"[41.05] 图片预规划完成: {len(image_plan)} 张")
        except Exception as error:
            logger.warning(f"[41.05] 图片预规划失败: {error}")
    return result


def check_knowledge_node(state, *, search_coordinator):
    search_count = state.get("search_count", 0)
    max_count = state.get("max_search_count", 5)
    logger.info(
        f"=== Step 3.5: 知识空白检查 (搜索次数: {search_count}/{max_count}) ==="
    )
    return search_coordinator.run(state)


def refine_search_node(state, *, search_coordinator):
    search_count = state.get("search_count", 0) + 1
    logger.info(f"=== Step 3.6: 细化搜索 (第 {search_count} 轮) ===")
    result = search_coordinator.refine_search(state.get("knowledge_gaps", []), state)
    if result.get("success"):
        logger.info(f"细化搜索完成: 获取 {len(result.get('results', []))} 条结果")
    else:
        logger.warning(f"细化搜索失败: {result.get('reason', '未知原因')}")
    return state


def enhance_with_knowledge_node(
    state,
    *,
    writer,
    parallel_executor,
    prompt_manager_factory,
    task_config_factory,
):
    logger.info("=== Step 3.7: 知识增强 ===")
    sections = state.get("sections", [])
    gaps = state.get("knowledge_gaps", [])
    new_knowledge = state.get("accumulated_knowledge", "")
    if not gaps or not new_knowledge:
        logger.info("没有需要增强的内容")
        return state

    prompt_manager = prompt_manager_factory()
    enhance_items = []
    for section in sections:
        section_gaps = [
            gap
            for gap in gaps
            if not gap.get("section_id")
            or gap.get("section_id") == section.get("id")
        ]
        if section_gaps:
            enhance_items.append((section, section_gaps))
    if not enhance_items:
        logger.info("没有需要增强的章节")
        state["knowledge_gaps"] = []
        return state

    def enhance_single(section, section_gaps):
        prompt = prompt_manager.render_writer_enhance_with_knowledge(
            original_content=section.get("content", ""),
            new_knowledge=new_knowledge,
            knowledge_gaps=section_gaps,
        )
        return writer.llm.chat(messages=[{"role": "user", "content": prompt}])

    tasks = [
        {
            "name": f"增强-{section.get('title', '')}",
            "fn": enhance_single,
            "args": (section, section_gaps),
        }
        for section, section_gaps in enhance_items
    ]
    results = parallel_executor.run_parallel(
        tasks,
        config=task_config_factory(name="knowledge_enhance", timeout_seconds=120),
    )
    for index, result in enumerate(results):
        if result.success:
            enhance_items[index][0]["content"] = result.result
            logger.info(
                f"章节增强完成: {enhance_items[index][0].get('title', '')}"
            )
        else:
            logger.error(f"章节增强失败: {result.error}")
    enhanced_count = sum(1 for result in results if result.success)
    logger.info(f"知识增强完成: {enhanced_count} 个章节")
    state["knowledge_gaps"] = []
    return state
