"""Task lifecycle and result finalization helpers."""

from .result_pipeline import (
    GenerationResult,
    GenerationResultPipeline,
    GenerationResultRequest,
)
from .progress_events import (
    STAGE_PROGRESS,
    normalize_research_result,
    project_generation_event,
)
from .task_events import SSELogHandler, TaskEventBridge

__all__ = [
    "GenerationResult",
    "GenerationResultPipeline",
    "GenerationResultRequest",
    "STAGE_PROGRESS",
    "SSELogHandler",
    "TaskEventBridge",
    "normalize_research_result",
    "project_generation_event",
]
