"""LangGraph workflow construction."""

from langgraph.graph import END, START, StateGraph

from ..schemas.state import SharedState


class GraphBuilder:
    def __init__(self, generator):
        self.generator = generator

    def build(self):
        generator = self.generator
        workflow = StateGraph(SharedState)

        nodes = (
            ("researcher", generator._researcher_node),
            ("planner", generator._planner_node),
            ("writer", generator._writer_node),
            ("check_knowledge", generator._check_knowledge_node),
            ("refine_search", generator._refine_search_node),
            ("enhance_with_knowledge", generator._enhance_with_knowledge_node),
            ("questioner", generator._questioner_node),
            ("deepen_content", generator._deepen_content_node),
            ("coder_and_artist", generator._coder_and_artist_node),
            ("cross_section_dedup", generator._cross_section_dedup_node),
            ("section_evaluate", generator._section_evaluate_node),
            ("section_improve", generator._section_improve_node),
            ("consistency_check", generator._consistency_check_node),
            ("reviewer", generator._reviewer_node),
            ("revision", generator._revision_node),
            ("factcheck", generator._factcheck_node),
            ("text_cleanup", generator._text_cleanup_node),
            ("humanizer", generator._humanizer_node),
            ("wait_for_images", generator._wait_for_images_node),
            ("assembler", generator._assembler_node),
            ("summary_generator", generator._summary_generator_node),
        )
        for node_name, handler in nodes:
            generator._add_node(workflow, node_name, handler)

        workflow.add_edge(START, "researcher")
        workflow.add_edge("researcher", "planner")
        workflow.add_edge("planner", "writer")
        workflow.add_conditional_edges(
            "writer",
            generator._should_check_knowledge,
            {"check": "check_knowledge", "skip": "questioner"},
        )
        workflow.add_conditional_edges(
            "check_knowledge",
            generator._should_refine_search,
            {"search": "refine_search", "continue": "questioner"},
        )
        workflow.add_edge("refine_search", "enhance_with_knowledge")
        workflow.add_edge("enhance_with_knowledge", "check_knowledge")
        workflow.add_conditional_edges(
            "questioner",
            generator._should_deepen,
            {"deepen": "deepen_content", "continue": "section_evaluate"},
        )
        workflow.add_conditional_edges(
            "deepen_content",
            generator._should_continue_questioning,
            {"questioner": "questioner", "section_evaluate": "section_evaluate"},
        )
        workflow.add_conditional_edges(
            "section_evaluate",
            generator._should_improve_sections,
            {"improve": "section_improve", "continue": "coder_and_artist"},
        )
        workflow.add_edge("section_improve", "section_evaluate")
        workflow.add_edge("coder_and_artist", "cross_section_dedup")
        workflow.add_edge("cross_section_dedup", "consistency_check")
        workflow.add_edge("consistency_check", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            generator._should_revise,
            {"revision": "revision", "assemble": "factcheck"},
        )
        workflow.add_edge("revision", "reviewer")
        workflow.add_edge("factcheck", "text_cleanup")
        workflow.add_edge("text_cleanup", "humanizer")
        workflow.add_edge("humanizer", "wait_for_images")
        workflow.add_edge("wait_for_images", "assembler")
        workflow.add_edge("assembler", "summary_generator")
        workflow.add_edge("summary_generator", END)

        return workflow
