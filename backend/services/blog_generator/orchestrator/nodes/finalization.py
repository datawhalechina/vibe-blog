"""Code, image, cleanup, and assembly node handlers."""

import copy
import logging

from . import is_enabled, resolve_style

logger = logging.getLogger("services.blog_generator.generator")
_MISSING_IMAGE_TASK = object()


def coder_and_artist_node(
    state,
    *,
    coder,
    artist,
    image_task_registry,
    executor_factory,
    uuid_factory,
):
    logger.info("=== Step 5: 代码生成 + 配图异步启动 ===")
    try:
        state = coder.run(state)
    except Exception as error:
        logger.error(f"代码生成失败: {error}")
    logger.info(f"代码生成完成: {len(state.get('code_blocks', []))} 个代码块")

    state["sections"] = artist.preprocess_ascii_flowcharts(
        state.get("sections", [])
    )
    artist_state = copy.deepcopy(state)
    image_executor = executor_factory(
        max_workers=1, thread_name_prefix="artist"
    )
    future = image_executor.submit(artist.run, artist_state)
    image_task_id = uuid_factory()
    image_task_registry.register(image_task_id, future, image_executor)
    state["_image_task_id"] = image_task_id
    logger.info("配图生成已异步启动，不阻塞后续流程")
    return state


def wait_for_images_node(
    state,
    *,
    image_task_registry,
    tracker,
    timeout,
):
    image_task_id = state.pop("_image_task_id", None)
    if not image_task_id:
        logger.warning("无配图异步任务，跳过等待")
        return state
    logger.info("=== 等待配图生成完成 ===")
    try:
        result = image_task_registry.pop(
            image_task_id,
            timeout=timeout,
            default=_MISSING_IMAGE_TASK,
        )
        if result is _MISSING_IMAGE_TASK:
            logger.warning("无配图异步任务，跳过等待")
            return state
        if isinstance(result, dict):
            if "section_images" in result:
                state["section_images"] = result["section_images"]
                logger.info(
                    f"合并 section_images: {len(state['section_images'])} 张"
                )
            if "images" in result:
                state["images"] = result["images"]
            merge_artist_image_ids(
                state.get("sections", []), result.get("sections", [])
            )
        logger.info(f"=== 配图生成完成: {len(state.get('images', []))} 张图片 ===")
        for image in state.get("images", []):
            tracker.log_image_generation(
                image_id=image.get("id", ""),
                image_type=image.get("render_method", ""),
                success=True,
            )
    except Exception as error:
        logger.error(f"配图生成失败或超时: {error}")
    return state


def merge_artist_image_ids(current_sections, artist_sections):
    artist_by_id = {
        section.get("id"): section
        for section in artist_sections
        if section.get("id")
    }
    for index, current in enumerate(current_sections):
        artist_section = artist_by_id.get(current.get("id"))
        if artist_section is None and index < len(artist_sections):
            artist_section = artist_sections[index]
        if not artist_section:
            continue
        image_ids = artist_section.get("image_ids", [])
        if image_ids:
            current["image_ids"] = list(
                dict.fromkeys(current.get("image_ids", []) + image_ids)
            )


def factcheck_node(
    state,
    *,
    factcheck,
    configured_style,
    env_factcheck,
):
    if state.get("target_length", "medium") == "mini":
        logger.info("[FactCheck] mini 模式，跳过事实核查")
        return state
    if not is_enabled(
        env_factcheck, resolve_style(state, configured_style).enable_fact_check
    ):
        logger.info("=== Step 7.3: 事实核查（已禁用，跳过）===")
        return state
    logger.info("=== Step 7.3: 事实核查 ===")
    try:
        return factcheck.run(state)
    except Exception as error:
        logger.error(f"[FactCheck] 异常，降级跳过: {error}")
        return state


def text_cleanup_node(
    state,
    *,
    cleanup,
    configured_style,
    env_text_cleanup,
):
    if not is_enabled(
        env_text_cleanup, resolve_style(state, configured_style).enable_text_cleanup
    ):
        logger.info("=== Step 7.4: 文本清理（已禁用，跳过）===")
        return state
    logger.info("=== Step 7.4: 确定性文本清理 ===")
    total_fixes = 0
    for section in state.get("sections", []):
        content = section.get("content", "")
        if not content:
            continue
        result = cleanup(content)
        section["content"] = result["text"]
        fixes = result["total_fixes"]
        if fixes:
            logger.info(
                f"  [{section.get('title', '')}] 修复 {fixes} 处: {result['stats']}"
            )
            total_fixes += fixes
    logger.info(f"[TextCleanup] 完成: 共修复 {total_fixes} 处")
    return state


def humanizer_node(
    state,
    *,
    humanizer,
    configured_style,
    env_humanizer,
):
    if not is_enabled(
        env_humanizer, resolve_style(state, configured_style).enable_humanizer
    ):
        logger.info("=== Step 7.5: 去 AI 味（已禁用，跳过）===")
        return state
    logger.info("=== Step 7.5: 去 AI 味 ===")
    try:
        return humanizer.run(state)
    except Exception as error:
        logger.error(f"[Humanizer] 异常，降级使用原始内容: {error}")
        return state


def assembler_node(state, *, assembler):
    logger.info("=== Step 8: 文档组装 ===")
    return assembler.run(state)


def summary_generator_node(
    state,
    *,
    summary_generator,
    configured_style,
    env_summary,
):
    if not is_enabled(
        env_summary, resolve_style(state, configured_style).enable_summary_gen
    ):
        logger.info("=== Step 9: 导读+SEO（已禁用，跳过）===")
        return state
    logger.info("=== Step 9: 导读 + SEO 关键词生成 ===")
    try:
        return summary_generator.run(state)
    except Exception as error:
        logger.error(f"[SummaryGenerator] 异常，降级跳过: {error}")
        return state
