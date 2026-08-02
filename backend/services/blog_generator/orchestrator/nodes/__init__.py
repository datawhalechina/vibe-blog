"""Module-level LangGraph node handlers."""

import logging

from ...style_profile import StyleProfile


logger = logging.getLogger("services.blog_generator.generator")


def validate_layer(layer_validator, layer_name, state):
    if not layer_validator:
        return
    try:
        ok, missing = layer_validator.validate_inputs(layer_name, state)
        if not ok:
            logger.warning(f"🏗️ [{layer_name}] 层输入缺失: {missing}")
    except Exception as error:
        logger.debug(f"层校验异常: {error}")


def resolve_style(state, configured_style):
    if configured_style:
        return configured_style
    return StyleProfile.from_target_length(state.get("target_length", "medium"))


def is_enabled(environment_flag, style_flag):
    return environment_flag and style_flag
