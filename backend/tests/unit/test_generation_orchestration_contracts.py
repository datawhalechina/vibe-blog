import inspect
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.blog_generator.blog_service import BlogService
from services.blog_generator.generator import BlogGenerator
from services.blog_generator.lifecycle.result_pipeline import (
    GenerationResultPipeline,
    GenerationResultRequest,
)
from services.blog_generator.lifecycle.task_events import TaskEventBridge
from services.blog_generator.orchestrator.execution_runner import GraphExecutionRunner
from services.blog_generator.orchestrator.graph_builder import GraphBuilder


def test_blog_service_preserves_generation_facade_signatures():
    expected = {
        "generate_sync": "(self, topic: str, article_type: str = 'tutorial', target_audience: str = 'intermediate', target_length: str = 'medium', source_material: str = None) -> Dict[str, Any]",
        "generate_async": "(self, task_id: str, topic: str, article_type: str = 'tutorial', target_audience: str = 'intermediate', audience_adaptation: str = 'default', target_length: str = 'medium', source_material: str = None, document_ids: list = None, document_knowledge: list = None, image_style: str = '', generate_images: bool = True, generate_cover_video: bool = False, video_aspect_ratio: str = '16:9', custom_config: dict = None, deep_thinking: bool = False, background_investigation: bool = True, interactive: bool = False, task_manager=None, app=None)",
        "_run_generation": "(self, task_id: str, topic: str, article_type: str, target_audience: str, audience_adaptation: str, target_length: str, source_material: str, document_ids: list = None, document_knowledge: list = None, image_style: str = '', generate_images: bool = True, generate_cover_video: bool = False, video_aspect_ratio: str = '16:9', custom_config: dict = None, deep_thinking: bool = False, background_investigation: bool = True, interactive: bool = False, task_manager=None)",
        "_run_resume": "(self, task_id: str, resume_value, config: dict, task_manager=None, task_info: dict = None)",
        "_save_markdown": "(self, task_id: str, markdown: str, outline: Dict[str, Any], cover_image_path: Optional[str] = None) -> Optional[str]",
    }

    assert {
        name: str(inspect.signature(BlogService.__dict__[name])) for name in expected
    } == expected
    assert not {
        "_generate_cover_image",
        "_generate_cover_video",
        "_generate_sequence_video",
        "_merge_videos",
    } & set(BlogService.__dict__)


def test_blog_generator_preserves_build_and_execution_signatures():
    expected = {
        "_build_workflow": "(self) -> langgraph.graph.state.StateGraph",
        "compile": "(self, checkpointer=None)",
        "generate": "(self, topic: str, article_type: str = 'tutorial', target_audience: str = 'intermediate', target_length: str = 'medium', source_material: str = None, on_progress: Callable[[str, str], NoneType] = None) -> Dict[str, Any]",
        "generate_stream": "(self, topic: str, article_type: str = 'tutorial', target_audience: str = 'intermediate', target_length: str = 'medium', source_material: str = None)",
    }

    assert {
        name: str(inspect.signature(BlogGenerator.__dict__[name])) for name in expected
    } == expected


def test_graph_builder_preserves_workflow_topology():
    generator = BlogGenerator(MagicMock())

    workflow = GraphBuilder(generator).build()

    assert set(workflow.nodes) == {
        "researcher",
        "planner",
        "writer",
        "check_knowledge",
        "refine_search",
        "enhance_with_knowledge",
        "questioner",
        "deepen_content",
        "coder_and_artist",
        "cross_section_dedup",
        "section_evaluate",
        "section_improve",
        "consistency_check",
        "reviewer",
        "revision",
        "factcheck",
        "text_cleanup",
        "humanizer",
        "wait_for_images",
        "assembler",
        "summary_generator",
    }
    assert set(workflow.edges) == {
        ("__start__", "researcher"),
        ("researcher", "planner"),
        ("planner", "writer"),
        ("refine_search", "enhance_with_knowledge"),
        ("enhance_with_knowledge", "check_knowledge"),
        ("section_improve", "section_evaluate"),
        ("coder_and_artist", "cross_section_dedup"),
        ("cross_section_dedup", "consistency_check"),
        ("consistency_check", "reviewer"),
        ("revision", "reviewer"),
        ("factcheck", "text_cleanup"),
        ("text_cleanup", "humanizer"),
        ("humanizer", "wait_for_images"),
        ("wait_for_images", "assembler"),
        ("assembler", "summary_generator"),
        ("summary_generator", "__end__"),
    }
    assert {
        source: {name: branch.ends for name, branch in branches.items()}
        for source, branches in workflow.branches.items()
    } == {
        "writer": {
            "_should_check_knowledge": {
                "check": "check_knowledge",
                "skip": "questioner",
            }
        },
        "check_knowledge": {
            "_should_refine_search": {
                "search": "refine_search",
                "continue": "questioner",
            }
        },
        "questioner": {
            "_should_deepen": {
                "deepen": "deepen_content",
                "continue": "section_evaluate",
            }
        },
        "deepen_content": {
            "_should_continue_questioning": {
                "questioner": "questioner",
                "section_evaluate": "section_evaluate",
            }
        },
        "section_evaluate": {
            "_should_improve_sections": {
                "improve": "section_improve",
                "continue": "coder_and_artist",
            }
        },
        "reviewer": {
            "_should_revise": {
                "revision": "revision",
                "assemble": "factcheck",
            }
        },
    }


def test_task_event_bridge_attaches_injects_and_closes_idempotently():
    task_manager = MagicMock()
    task_manager.get_queue.return_value = object()
    generator = SimpleNamespace(
        llm=SimpleNamespace(),
        researcher=SimpleNamespace(search_service=SimpleNamespace()),
        writer=SimpleNamespace(),
    )
    bridge = TaskEventBridge(generator, task_manager, "task-1")

    bridge.attach()
    bridge.inject_dependencies()
    handler = bridge.handler

    assert all(
        bridge.handler in logging.getLogger(name).handlers
        for name in bridge.logger_names
    )
    assert generator.llm.task_manager is task_manager
    assert generator.researcher.task_id == "task-1"
    assert generator.researcher.search_service.task_manager is task_manager
    assert generator.writer.task_id == "task-1"

    bridge.close()
    bridge.close()

    assert all(
        handler not in logging.getLogger(name).handlers
        for name in bridge.logger_names
    )


def test_facades_compose_the_extracted_components():
    service = BlogService.__new__(BlogService)
    service.generator = MagicMock()

    assert isinstance(GenerationResultPipeline(service), GenerationResultPipeline)
    assert isinstance(GraphExecutionRunner(service.generator), GraphExecutionRunner)


def test_blog_generator_generate_delegates_to_execution_runner():
    generator = BlogGenerator.__new__(BlogGenerator)
    generator._execution_runner = MagicMock()
    generator._execution_runner.generate.return_value = {"success": True}

    result = generator.generate(
        "Topic",
        article_type="guide",
        target_audience="advanced",
        target_length="long",
        source_material="Source",
        on_progress=MagicMock(),
    )

    assert result == {"success": True}
    generator._execution_runner.generate.assert_called_once_with(
        topic="Topic",
        article_type="guide",
        target_audience="advanced",
        target_length="long",
        source_material="Source",
        on_progress=generator._execution_runner.generate.call_args.kwargs["on_progress"],
    )


@pytest.mark.asyncio
async def test_blog_generator_generate_stream_delegates_to_execution_runner():
    generator = BlogGenerator.__new__(BlogGenerator)

    async def events(**kwargs):
        assert kwargs == {
            "topic": "Topic",
            "article_type": "guide",
            "target_audience": "advanced",
            "target_length": "long",
            "source_material": "Source",
        }
        yield {"stage": "writer", "state": {}}

    generator._execution_runner = SimpleNamespace(generate_stream=events)

    result = [
        event
        async for event in generator.generate_stream(
            "Topic", "guide", "advanced", "long", "Source"
        )
    ]

    assert result == [{"stage": "writer", "state": {}}]


def test_result_pipeline_uses_facade_hooks_and_persists_before_completion():
    service = MagicMock()
    service._validate_final_state.return_value = "# Body"
    generate_cover_image = MagicMock(return_value=(
        "https://example.com/cover.png",
        "/tmp/cover.png",
        "Summary",
    ))
    service._save_markdown.return_value = "/tmp/article.md"
    generate_cover_video = MagicMock(return_value="/tmp/cover.mp4")
    service.generator = SimpleNamespace(llm=MagicMock(), _memory_storage=None)
    task_manager = MagicMock()
    db_service = MagicMock()
    manager = MagicMock()
    manager.attach_mock(db_service.save_history, "save_history")
    manager.attach_mock(service._send_completion_event, "send_completion")
    final_state = {
        "final_markdown": "# Body",
        "outline": {"title": "Title"},
        "sections": [{}],
        "images": [],
        "code_blocks": [],
        "search_results": [
            {"url": "https://example.com/source", "title": "Source"}
        ],
    }
    request = GenerationResultRequest(
        task_id="task-1",
        topic="Topic",
        article_type="tutorial",
        target_length="short",
        final_state=final_state,
        article_config={"sections_count": 1, "target_word_count": 1000},
        generate_images=True,
        generate_cover_video=True,
        video_aspect_ratio="16:9",
        task_manager=task_manager,
    )

    with patch(
        "services.database_service.get_db_service", return_value=db_service
    ):
        result = GenerationResultPipeline(
            service,
            generate_cover_image_fn=generate_cover_image,
            generate_cover_video_fn=generate_cover_video,
        ).finalize(request)

    assert result.saved_path == "/tmp/article.md"
    assert result.cover_video_path == "/tmp/cover.mp4"
    assert result.citations == [
        {
            "url": "https://example.com/source",
            "title": "Source",
            "domain": "example.com",
            "snippet": "",
        }
    ]
    assert [call[0] for call in manager.mock_calls[:2]] == [
        "save_history",
        "send_completion",
    ]
    generate_cover_image.assert_called_once()
    service._save_markdown.assert_called_once()
    generate_cover_video.assert_called_once()


def test_result_pipeline_completes_when_media_generation_degrades():
    service = MagicMock()
    service._validate_final_state.return_value = "# Body"
    service._save_markdown.return_value = "/tmp/article.md"
    service.generator = SimpleNamespace(llm=MagicMock(), _memory_storage=None)
    task_manager = MagicMock()
    db_service = MagicMock()
    request = GenerationResultRequest(
        task_id="task-1",
        topic="Topic",
        article_type="tutorial",
        target_length="short",
        final_state={
            "final_markdown": "# Body",
            "outline": {"title": "Title"},
            "sections": [{}],
            "images": [],
            "code_blocks": [],
        },
        article_config={},
        generate_images=True,
        generate_cover_video=True,
        video_aspect_ratio="16:9",
        task_manager=task_manager,
    )

    with patch(
        "services.database_service.get_db_service", return_value=db_service
    ):
        result = GenerationResultPipeline(
            service,
            generate_cover_image_fn=MagicMock(return_value=None),
            generate_cover_video_fn=MagicMock(return_value=None),
        ).finalize(request)

    assert result.markdown == "# Body"
    assert result.cover_video_path is None
    db_service.save_history.assert_called_once()
    service._send_completion_event.assert_called_once()


def test_result_pipeline_completes_when_optional_video_service_resolution_fails():
    service = MagicMock()
    service._validate_final_state.return_value = "# Body"
    service._save_markdown.return_value = "/tmp/article.md"
    service.generator = SimpleNamespace(llm=MagicMock(), _memory_storage=None)
    db_service = MagicMock()
    get_oss_service = MagicMock(side_effect=RuntimeError("oss unavailable"))
    request = GenerationResultRequest(
        task_id="task-1",
        topic="Topic",
        article_type="tutorial",
        target_length="short",
        final_state={
            "final_markdown": "# Body",
            "outline": {"title": "Title"},
            "sections": [{}],
            "images": [],
            "code_blocks": [],
        },
        article_config={},
        generate_images=True,
        generate_cover_video=True,
        video_aspect_ratio="16:9",
    )

    with patch("services.database_service.get_db_service", return_value=db_service):
        result = GenerationResultPipeline(
            service,
            generate_cover_image_fn=MagicMock(
                return_value=("https://example.com/cover.png", "/tmp/cover.png", "Summary")
            ),
            get_video_service_fn=MagicMock(return_value=None),
            get_oss_service_fn=get_oss_service,
        ).finalize(request)

    assert result.cover_video_path is None
    get_oss_service.assert_not_called()
    db_service.save_history.assert_called_once()
    service._send_completion_event.assert_called_once()


def test_result_pipeline_completes_when_oss_service_resolution_raises():
    service = MagicMock()
    service._validate_final_state.return_value = "# Body"
    service._save_markdown.return_value = "/tmp/article.md"
    service.generator = SimpleNamespace(llm=MagicMock(), _memory_storage=None)
    db_service = MagicMock()
    video_service = MagicMock()
    video_service.is_available.return_value = True
    request = GenerationResultRequest(
        task_id="task-1",
        topic="Topic",
        article_type="tutorial",
        target_length="short",
        final_state={
            "final_markdown": "# Body",
            "outline": {"title": "Title"},
            "sections": [{}],
            "images": [],
            "code_blocks": [],
        },
        article_config={},
        generate_images=True,
        generate_cover_video=True,
        video_aspect_ratio="16:9",
    )

    with patch("services.database_service.get_db_service", return_value=db_service):
        result = GenerationResultPipeline(
            service,
            generate_cover_image_fn=MagicMock(
                return_value=("https://example.com/cover.png", "/tmp/cover.png", "Summary")
            ),
            get_video_service_fn=MagicMock(return_value=video_service),
            get_oss_service_fn=MagicMock(side_effect=RuntimeError("oss unavailable")),
        ).finalize(request)

    assert result.cover_video_path is None
    video_service.generate_from_image.assert_not_called()
    db_service.save_history.assert_called_once()
    service._send_completion_event.assert_called_once()


def test_run_generation_uses_task_event_bridge_for_setup_and_cleanup():
    service = BlogService.__new__(BlogService)
    snapshot = SimpleNamespace(
        next=(),
        tasks=(),
        values={"error": "provider unavailable", "final_markdown": ""},
    )
    app = MagicMock()
    app.stream.return_value = []
    app.get_state.return_value = snapshot
    service.generator = SimpleNamespace(app=app, llm=MagicMock())
    service._interrupted_tasks = {}
    task_manager = MagicMock()
    bridge = MagicMock()
    bridge.handler = None
    bridge.logger_names = ()

    with (
        patch.dict(
            "os.environ",
            {"TOKEN_TRACKING_ENABLED": "false", "BLOG_TASK_LOG_ENABLED": "false"},
        ),
        patch("time.sleep"),
        patch("logging_config.create_task_logger", return_value=None),
        patch(
            "services.blog_generator.blog_service.TaskEventBridge",
            return_value=bridge,
        ) as bridge_class,
        patch("services.blog_generator.blog_service.update_queue_status"),
    ):
        service._run_generation(
            task_id="task-1",
            topic="topic",
            article_type="tutorial",
            target_audience="developers",
            audience_adaptation="default",
            target_length="short",
            source_material="",
            generate_images=False,
            task_manager=task_manager,
        )

    bridge_class.assert_called_once_with(service.generator, task_manager, "task-1")
    bridge.attach.assert_called_once_with()
    bridge.inject_dependencies.assert_called_once_with()
    bridge.close.assert_called_once_with()
