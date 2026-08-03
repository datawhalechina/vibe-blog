from unittest.mock import MagicMock

import pytest


def _project_event(**kwargs):
    from services.blog_generator.lifecycle.progress_events import (
        project_generation_event,
    )

    defaults = {
        "task_manager": MagicMock(),
        "task_id": "task-1",
        "node_name": "unknown_node",
        "state": {},
        "completed_sections": 0,
        "interactive": False,
        "token_usage": None,
        "initial_generation": True,
        "update_queue_progress_fn": MagicMock(),
    }
    defaults.update(kwargs)
    return project_generation_event(**defaults), defaults


def _events(task_manager, event_name):
    return [
        call.args[2]
        for call in task_manager.send_event.call_args_list
        if call.args[1] == event_name
    ]


def test_projects_progress_with_token_usage_and_queue_update():
    task_manager = MagicMock()
    update_queue = MagicMock()

    (completed, inputs) = _project_event(
        task_manager=task_manager,
        node_name="writer",
        token_usage={"total_tokens": 42},
        update_queue_progress_fn=update_queue,
    )

    assert completed == 0
    assert _events(task_manager, "progress") == [
        {
            "stage": "writer",
            "progress": 45,
            "message": "正在撰写内容...",
            "token_usage": {"total_tokens": 42},
        }
    ]
    update_queue.assert_called_once_with(
        "task-1", 45, stage="正在撰写内容...", detail="writer"
    )
    assert inputs["completed_sections"] == 0


def test_unknown_node_preserves_generic_progress_contract():
    task_manager = MagicMock()

    (completed, _) = _project_event(
        task_manager=task_manager,
        node_name="custom_stage",
    )

    assert completed == 0
    assert _events(task_manager, "progress") == [
        {
            "stage": "custom_stage",
            "progress": 50,
            "message": "正在执行 custom_stage...",
        }
    ]
    assert _events(task_manager, "result") == []


def test_writer_projects_only_new_sections_and_updates_count():
    task_manager = MagicMock()
    sections = [
        {"title": "One", "content": "First"},
        {"title": "Two", "content": "Second"},
    ]

    (completed, _) = _project_event(
        task_manager=task_manager,
        node_name="writer",
        state={"sections": sections},
        completed_sections=1,
    )

    assert completed == 2
    assert _events(task_manager, "result") == [
        {
            "type": "section_complete",
            "data": {
                "section_index": 2,
                "title": "Two",
                "content": "Second",
                "content_length": 6,
                "message": "章节 2 撰写完成: Two",
            },
        }
    ]
    assert _events(task_manager, "writing_chunk") == [
        {
            "section_index": 2,
            "delta": "Second",
            "accumulated": "## One\n\nFirst\n\n## Two\n\nSecond",
        }
    ]


@pytest.mark.parametrize(
    ("node_name", "stage", "label"),
    [
        ("deepen_content", "deepen_complete", "内容深化完成"),
        ("revision", "revision_complete", "内容修订完成"),
        ("humanizer", "humanizer_complete", "文风优化完成"),
    ],
)
def test_whole_section_updates_share_the_existing_writing_chunk_shape(
    node_name, stage, label
):
    task_manager = MagicMock()

    (completed, _) = _project_event(
        task_manager=task_manager,
        node_name=node_name,
        state={"sections": [{"title": "One", "content": "Body"}]},
        completed_sections=1,
    )

    assert completed == 1
    assert _events(task_manager, "writing_chunk") == [
        {
            "section_index": 1,
            "delta": "",
            "accumulated": "## One\n\nBody",
            "stage": stage,
            "message": f"{label}，当前总字数: 14",
        }
    ]


@pytest.mark.parametrize("include_narrative", [True, False])
def test_outline_projection_preserves_initial_and_resume_payload_difference(
    include_narrative
):
    task_manager = MagicMock()
    outline = {
        "title": "Plan",
        "sections": [{"title": "One", "narrative_role": "setup"}],
        "narrative_mode": "journey",
        "narrative_flow": {"arc": "up"},
    }

    _project_event(
        task_manager=task_manager,
        node_name="planner",
        state={"outline": outline},
        interactive=True,
        initial_generation=include_narrative,
    )

    data = _events(task_manager, "result")[0]["data"]
    assert data["title"] == "Plan"
    assert data["sections_titles"] == ["One"]
    assert data["interactive"] is True
    narrative_keys = {
        "narrative_mode",
        "narrative_flow",
        "sections_narrative_roles",
    }
    assert (narrative_keys <= data.keys()) is include_narrative


def test_researcher_projects_search_cards_and_document_preview():
    task_manager = MagicMock()
    long_content = "x" * 501
    state = {
        "topic": "Topic",
        "background_knowledge": "Background",
        "key_concepts": ["one", "two"],
        "knowledge_source_stats": {"document_count": 1, "web_count": 1},
        "document_knowledge": [{"file_name": "doc.md", "content": long_content}],
        "search_results": [
            {
                "url": "https://example.com/path",
                "title": "Result",
                "content": "Snippet",
            }
        ],
    }

    _project_event(
        task_manager=task_manager,
        node_name="researcher",
        state=state,
    )

    results = _events(task_manager, "result")
    assert results[0] == {
        "type": "search_results",
        "data": {
            "query": "Topic",
            "results": [
                {
                    "url": "https://example.com/path",
                    "title": "Result",
                    "snippet": "Snippet",
                    "domain": "example.com",
                }
            ],
        },
    }
    assert results[1]["type"] == "researcher_complete"
    assert results[1]["data"]["document_previews"] == [
        {
            "file_name": "doc.md",
            "preview": "x" * 500 + "...",
            "total_length": 501,
        }
    ]


@pytest.mark.parametrize(
    ("node_name", "state", "result_type"),
    [
        ("check_knowledge", {"knowledge_gaps": []}, "check_knowledge_complete"),
        ("refine_search", {"search_history": []}, "refine_search_complete"),
        ("enhance_with_knowledge", {}, "enhance_knowledge_complete"),
        ("questioner", {}, "questioner_complete"),
        ("coder", {"code_blocks": [{}]}, "coder_complete"),
        ("artist", {"images": [{}]}, "artist_complete"),
        ("reviewer", {"review_score": 88}, "reviewer_complete"),
        ("assembler", {"final_markdown": "# Post"}, "assembler_complete"),
    ],
)
def test_projects_existing_node_result_types(node_name, state, result_type):
    task_manager = MagicMock()

    _project_event(
        task_manager=task_manager,
        node_name=node_name,
        state=state,
    )

    assert _events(task_manager, "result")[0]["type"] == result_type


@pytest.mark.parametrize(
    ("node_name", "state"),
    [
        ("check_knowledge", {"knowledge_gaps": []}),
        ("refine_search", {"search_history": []}),
        ("enhance_with_knowledge", {}),
        ("questioner", {}),
        ("coder", {"code_blocks": [{}]}),
        ("artist", {"images": [{}]}),
    ],
)
def test_resume_projection_does_not_add_initial_only_result_events(
    node_name, state
):
    task_manager = MagicMock()

    _project_event(
        task_manager=task_manager,
        node_name=node_name,
        state=state,
        initial_generation=False,
    )

    assert _events(task_manager, "result") == []


def test_resume_researcher_preserves_the_old_generic_progress_fallback():
    task_manager = MagicMock()

    _project_event(
        task_manager=task_manager,
        node_name="researcher",
        state={},
        initial_generation=False,
    )

    assert _events(task_manager, "progress") == [
        {
            "stage": "researcher",
            "progress": 50,
            "message": "正在执行 researcher...",
        }
    ]
    assert _events(task_manager, "result") == []


def test_missing_task_manager_has_no_side_effects():
    update_queue = MagicMock()

    (completed, _) = _project_event(
        task_manager=None,
        node_name="writer",
        state={"sections": [{"title": "One", "content": "Body"}]},
        completed_sections=0,
        update_queue_progress_fn=update_queue,
    )

    assert completed == 0
    update_queue.assert_not_called()
