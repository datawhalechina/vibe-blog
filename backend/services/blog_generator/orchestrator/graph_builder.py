"""LangGraph workflow construction from explicit handler mappings."""

from langgraph.graph import END, START, StateGraph

from ..schemas.state import SharedState
from ..schemas.state_contracts import wrap_node_state_contract


NODE_NAMES = (
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
)

ROUTING_NAMES = (
    "should_check_knowledge",
    "should_refine_search",
    "should_deepen",
    "should_continue_questioning",
    "should_improve_sections",
    "should_revise",
)


class GraphBuilder:
    def __init__(self, *, node_handlers, routing_handlers, middleware_pipeline):
        self.node_handlers = dict(node_handlers)
        self.routing_handlers = dict(routing_handlers)
        self.middleware_pipeline = middleware_pipeline
        self._validate_keys("node", self.node_handlers, NODE_NAMES)
        self._validate_keys("routing", self.routing_handlers, ROUTING_NAMES)

    @staticmethod
    def _validate_keys(kind, handlers, expected):
        expected_keys = set(expected)
        actual_keys = set(handlers)
        if actual_keys != expected_keys:
            missing = sorted(expected_keys - actual_keys)
            extra = sorted(actual_keys - expected_keys)
            raise ValueError(
                f"Invalid {kind} handler keys: missing={missing}, extra={extra}"
            )

    def _add_node(self, workflow, node_name, handler):
        middleware_wrapped = self.middleware_pipeline.wrap_node(node_name, handler)
        workflow.add_node(
            node_name,
            wrap_node_state_contract(node_name, middleware_wrapped),
        )

    def build(self):
        workflow = StateGraph(SharedState)
        for node_name in NODE_NAMES:
            self._add_node(workflow, node_name, self.node_handlers[node_name])

        routes = self.routing_handlers
        workflow.add_edge(START, "researcher")
        workflow.add_edge("researcher", "planner")
        workflow.add_edge("planner", "writer")
        workflow.add_conditional_edges(
            "writer",
            routes["should_check_knowledge"],
            {"check": "check_knowledge", "skip": "questioner"},
        )
        workflow.add_conditional_edges(
            "check_knowledge",
            routes["should_refine_search"],
            {"search": "refine_search", "continue": "questioner"},
        )
        workflow.add_edge("refine_search", "enhance_with_knowledge")
        workflow.add_edge("enhance_with_knowledge", "check_knowledge")
        workflow.add_conditional_edges(
            "questioner",
            routes["should_deepen"],
            {"deepen": "deepen_content", "continue": "section_evaluate"},
        )
        workflow.add_conditional_edges(
            "deepen_content",
            routes["should_continue_questioning"],
            {"questioner": "questioner", "section_evaluate": "section_evaluate"},
        )
        workflow.add_conditional_edges(
            "section_evaluate",
            routes["should_improve_sections"],
            {"improve": "section_improve", "continue": "coder_and_artist"},
        )
        workflow.add_edge("section_improve", "section_evaluate")
        workflow.add_edge("coder_and_artist", "cross_section_dedup")
        workflow.add_edge("cross_section_dedup", "consistency_check")
        workflow.add_edge("consistency_check", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            routes["should_revise"],
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
