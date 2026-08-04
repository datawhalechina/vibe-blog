"""Run a BlogService graph stream and project its task events."""

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class GenerationStreamResult:
    completed_sections: int
    cancelled: bool = False


def run_generation_stream(
    *,
    app,
    stream_input: Any,
    config: dict,
    task_manager,
    task_id: str,
    interactive: bool,
    initial_generation: bool,
    get_token_usage_fn: Callable[[], Any],
    project_event_fn: Callable[..., int],
    update_queue_progress_fn: Callable[..., Any],
    on_cancel: Optional[Callable[[], None]] = None,
) -> GenerationStreamResult:
    """Iterate one graph stream while preserving task event semantics."""
    completed_sections = 0

    for event in app.stream(stream_input, config):
        if task_manager and task_manager.is_cancelled(task_id):
            if on_cancel:
                on_cancel()
            task_manager.send_event(
                task_id,
                "cancelled",
                {"task_id": task_id, "message": "任务已被用户取消"},
            )
            return GenerationStreamResult(
                completed_sections=completed_sections,
                cancelled=True,
            )

        for node_name, state in event.items():
            token_usage = get_token_usage_fn() if task_manager else None
            completed_sections = project_event_fn(
                task_manager=task_manager,
                task_id=task_id,
                node_name=node_name,
                state=state,
                completed_sections=completed_sections,
                interactive=interactive,
                token_usage=token_usage,
                initial_generation=initial_generation,
                update_queue_progress_fn=update_queue_progress_fn,
            )

    return GenerationStreamResult(completed_sections=completed_sections)


__all__ = ["GenerationStreamResult", "run_generation_stream"]
