"""Project LangGraph node state into the existing task progress contract."""

from types import MappingProxyType
from typing import Any, Callable, Mapping
from urllib.parse import urlparse


STAGE_PROGRESS = MappingProxyType(
    {
        "researcher": (10, "正在搜索资料..."),
        "planner": (25, "正在生成大纲..."),
        "writer": (45, "正在撰写内容..."),
        "check_knowledge": (52, "正在检查知识空白..."),
        "refine_search": (54, "正在补充搜索..."),
        "enhance_with_knowledge": (56, "正在增强内容..."),
        "questioner": (60, "正在检查内容深度..."),
        "deepen_content": (65, "正在深化内容..."),
        "coder": (75, "正在生成代码示例..."),
        "artist": (85, "正在生成配图..."),
        "reviewer": (90, "正在审核质量..."),
        "humanizer": (93, "正在优化文风..."),
        "revision": (95, "正在修订内容..."),
        "fact_checker": (96, "正在事实核查..."),
        "consistency_check": (97, "正在一致性检查..."),
        "assembler": (98, "正在组装文档..."),
    }
)


def normalize_research_result(state: Mapping[str, Any]):
    return (
        state.get("background_knowledge") or "",
        state.get("key_concepts") or [],
        state.get("knowledge_source_stats") or {},
        state.get("document_knowledge") or [],
        state.get("search_results") or [],
    )


def _sections_markdown(sections) -> str:
    return "".join(
        f"## {section.get('title', '')}\n\n{section.get('content', '')}\n\n"
        for section in sections
    )


def _project_researcher(task_manager, task_id: str, state: Mapping[str, Any]):
    background, key_concepts, knowledge_stats, doc_knowledge, raw_results = (
        normalize_research_result(state)
    )
    doc_previews = []
    for document in doc_knowledge[:3]:
        content = document.get("content", "")
        preview = content[:500] + "..." if len(content) > 500 else content
        doc_previews.append(
            {
                "file_name": document.get("file_name", "未知文档"),
                "preview": preview,
                "total_length": len(content),
            }
        )

    if raw_results:
        card_results = []
        for result in raw_results[:10]:
            url = result.get("url", "")
            try:
                domain = urlparse(url).hostname or ""
            except Exception:
                domain = ""
            card_results.append(
                {
                    "url": url,
                    "title": result.get("title", ""),
                    "snippet": (
                        result.get("content", "") or result.get("snippet", "")
                    )[:120],
                    "domain": domain,
                }
            )
        task_manager.send_event(
            task_id,
            "result",
            {
                "type": "search_results",
                "data": {"query": state.get("topic", ""), "results": card_results},
            },
        )

    task_manager.send_event(
        task_id,
        "result",
        {
            "type": "researcher_complete",
            "data": {
                "background_length": len(background),
                "key_concepts": key_concepts[:5] if key_concepts else [],
                "document_count": knowledge_stats.get("document_count", 0),
                "web_count": knowledge_stats.get("web_count", 0),
                "document_previews": doc_previews,
                "message": f"素材收集完成，获取 {len(background)} 字背景资料",
            },
        },
    )


def _project_outline(
    task_manager,
    task_id: str,
    state: Mapping[str, Any],
    *,
    interactive: bool,
    initial_generation: bool,
):
    outline = state.get("outline", {})
    sections = outline.get("sections", [])
    action = "生成完成" if initial_generation else "已确认"
    data = {
        "title": outline.get("title", ""),
        "sections_count": len(sections),
        "sections": sections,
        "sections_titles": [section.get("title", "") for section in sections],
        "message": (
            f"大纲{action}: {outline.get('title', '')} ({len(sections)} 章节)"
        ),
        "interactive": interactive,
    }
    if initial_generation:
        data.update(
            {
                "narrative_mode": outline.get("narrative_mode", ""),
                "narrative_flow": outline.get("narrative_flow", {}),
                "sections_narrative_roles": [
                    section.get("narrative_role", "") for section in sections
                ],
            }
        )
    task_manager.send_event(
        task_id,
        "result",
        {"type": "outline_complete", "data": data},
    )


def _project_writer(
    task_manager,
    task_id: str,
    sections,
    completed_sections: int,
) -> int:
    new_count = len(sections)
    if new_count <= completed_sections:
        return completed_sections
    for index in range(completed_sections, new_count):
        section = sections[index]
        task_manager.send_event(
            task_id,
            "result",
            {
                "type": "section_complete",
                "data": {
                    "section_index": index + 1,
                    "title": section.get("title", ""),
                    "content": section.get("content", ""),
                    "content_length": len(section.get("content", "")),
                    "message": (
                        f"章节 {index + 1} 撰写完成: {section.get('title', '')}"
                    ),
                },
            },
        )
        accumulated = _sections_markdown(sections[: index + 1])
        task_manager.send_event(
            task_id,
            "writing_chunk",
            {
                "section_index": index + 1,
                "delta": section.get("content", ""),
                "accumulated": accumulated.strip(),
            },
        )
    return new_count


def _project_whole_section_update(
    task_manager,
    task_id: str,
    sections,
    *,
    stage: str,
    label: str,
):
    accumulated = _sections_markdown(sections)
    task_manager.send_event(
        task_id,
        "writing_chunk",
        {
            "section_index": len(sections),
            "delta": "",
            "accumulated": accumulated.strip(),
            "stage": stage,
            "message": f"{label}，当前总字数: {len(accumulated)}",
        },
    )


def _project_node_result(task_manager, task_id: str, node_name: str, state):
    if node_name == "check_knowledge":
        gaps = state.get("knowledge_gaps", [])
        search_count = state.get("search_count", 0)
        max_search_count = state.get("max_search_count", 5)
        result_type = "check_knowledge_complete"
        data = {
            "gaps_count": len(gaps),
            "gaps": [gap.get("description", "") for gap in gaps[:3]],
            "search_count": search_count,
            "max_search_count": max_search_count,
            "message": (
                f"知识检查完成: 发现 {len(gaps)} 个空白点 "
                f"(搜索 {search_count}/{max_search_count})"
            ),
        }
    elif node_name == "refine_search":
        search_count = state.get("search_count", 0)
        max_search_count = state.get("max_search_count", 5)
        history = state.get("search_history", [])
        latest = history[-1] if history else {}
        result_type = "refine_search_complete"
        data = {
            "round": search_count,
            "max_rounds": max_search_count,
            "queries": latest.get("queries", []),
            "results_count": latest.get("results_count", 0),
            "message": (
                f"第 {search_count} 轮搜索完成: "
                f"获取 {latest.get('results_count', 0)} 条结果"
            ),
        }
    elif node_name == "enhance_with_knowledge":
        knowledge = state.get("accumulated_knowledge", "")
        result_type = "enhance_knowledge_complete"
        data = {
            "knowledge_length": len(knowledge),
            "message": f"内容增强完成: 累积知识 {len(knowledge)} 字",
        }
    elif node_name == "questioner":
        needs_deepen = state.get("needs_deepen", False)
        result_type = "questioner_complete"
        data = {
            "needs_deepen": needs_deepen,
            "message": "内容需要深化" if needs_deepen else "内容深度检查通过",
        }
    elif node_name == "coder" and state.get("code_blocks"):
        code_blocks = state.get("code_blocks", [])
        result_type = "coder_complete"
        data = {
            "code_blocks_count": len(code_blocks),
            "message": f"代码示例生成完成: {len(code_blocks)} 个代码块",
        }
    elif node_name == "artist" and state.get("images"):
        images = state.get("images", [])
        result_type = "artist_complete"
        data = {
            "images_count": len(images),
            "message": f"配图描述生成完成: {len(images)} 张",
        }
    elif node_name == "reviewer":
        score = state.get("review_score", 0)
        passed = state.get("review_passed", False)
        result_type = "reviewer_complete"
        data = {
            "score": score,
            "passed": passed,
            "message": f"质量审核完成: {score} 分 {'✅ 通过' if passed else '❌ 需修订'}",
        }
    elif node_name == "assembler":
        markdown = state.get("final_markdown", "")
        result_type = "assembler_complete"
        data = {
            "markdown_length": len(markdown),
            "message": f"文档组装完成: {len(markdown)} 字",
        }
    else:
        return
    task_manager.send_event(
        task_id,
        "result",
        {"type": result_type, "data": data},
    )


def project_generation_event(
    *,
    task_manager,
    task_id: str,
    node_name: str,
    state: Mapping[str, Any],
    completed_sections: int,
    interactive: bool,
    token_usage: Any,
    initial_generation: bool,
    update_queue_progress_fn: Callable[..., Any],
) -> int:
    """Emit the existing task events for one node and return section progress."""
    if not task_manager:
        return completed_sections

    default_progress = (50, f"正在执行 {node_name}...")
    progress, message = (
        STAGE_PROGRESS.get(node_name, default_progress)
        if initial_generation or node_name != "researcher"
        else default_progress
    )
    progress_data = {
        "stage": node_name,
        "progress": progress,
        "message": message,
    }
    if token_usage:
        progress_data["token_usage"] = token_usage
    task_manager.send_event(task_id, "progress", progress_data)
    update_queue_progress_fn(
        task_id,
        progress,
        stage=message,
        detail=node_name,
    )

    if node_name == "researcher" and initial_generation:
        _project_researcher(task_manager, task_id, state)
    elif node_name == "planner" and state.get("outline"):
        _project_outline(
            task_manager,
            task_id,
            state,
            interactive=interactive,
            initial_generation=initial_generation,
        )
    elif node_name == "writer" and state.get("sections"):
        completed_sections = _project_writer(
            task_manager,
            task_id,
            state.get("sections", []),
            completed_sections,
        )
    elif node_name in {"deepen_content", "revision", "humanizer"} and state.get(
        "sections"
    ):
        stage, label = {
            "deepen_content": ("deepen_complete", "内容深化完成"),
            "revision": ("revision_complete", "内容修订完成"),
            "humanizer": ("humanizer_complete", "文风优化完成"),
        }[node_name]
        _project_whole_section_update(
            task_manager,
            task_id,
            state.get("sections", []),
            stage=stage,
            label=label,
        )
    elif initial_generation or node_name not in {
        "researcher",
        "check_knowledge",
        "refine_search",
        "enhance_with_knowledge",
        "questioner",
        "coder",
        "artist",
    }:
        _project_node_result(task_manager, task_id, node_name, state)

    return completed_sections


__all__ = [
    "STAGE_PROGRESS",
    "normalize_research_result",
    "project_generation_event",
]
