"""
37.12 博客生成分层架构 — Layer 定义与层间契约校验

将 19 节点扁平 DAG 抽象为 7 层流水线：
  Research → Structure → Content → Enhancement → Validate → Quality → Output
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Criticality(str, Enum):
    HIGH = "high"
    LOW = "low"


@dataclass
class LoopConfig:
    max_rounds: int
    exit_field: str
    counter_field: str
    convergence_field: Optional[str] = None
    convergence_threshold: float = 0.3


@dataclass
class Layer:
    name: str
    description: str
    nodes: List[str]
    agents: List[str]
    required_inputs: List[str]
    outputs: List[str]
    optional_inputs: List[str] = field(default_factory=list)
    criticality: Criticality = Criticality.LOW
    parallel_groups: List[List[str]] = field(default_factory=list)
    loops: List[LoopConfig] = field(default_factory=list)
    style_switches: Dict[str, str] = field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        return self.criticality == Criticality.HIGH


# ==================== 7 层定义 ====================

BLOG_LAYERS: List[Layer] = [
    Layer(
        name="research",
        description="素材收集层",
        nodes=["researcher"],
        agents=["ResearcherAgent", "SearchCoordinator"],
        required_inputs=["topic", "article_type", "target_audience"],
        optional_inputs=["source_material"],
        outputs=["search_results", "background_knowledge", "key_concepts", "reference_links"],
        criticality=Criticality.LOW,
    ),
    Layer(
        name="structure",
        description="结构规划层",
        nodes=["planner"],
        agents=["PlannerAgent"],
        required_inputs=["topic", "article_type", "target_audience", "target_length"],
        optional_inputs=["background_knowledge", "key_concepts"],
        outputs=["outline"],
        criticality=Criticality.HIGH,
    ),
    Layer(
        name="content",
        description="内容生成层",
        nodes=[
            "writer",
            "check_knowledge", "refine_search", "enhance_with_knowledge",
            "questioner", "deepen_content",
            "section_evaluate", "section_improve",
        ],
        agents=["WriterAgent", "SearchCoordinator", "QuestionerAgent"],
        required_inputs=["outline"],
        optional_inputs=["background_knowledge", "target_length"],
        outputs=[
            "sections", "question_results", "all_sections_detailed",
            "questioning_count", "section_evaluations", "accumulated_knowledge",
        ],
        criticality=Criticality.HIGH,
        loops=[
            LoopConfig(max_rounds=5, exit_field="knowledge_gaps_empty", counter_field="search_count"),
            LoopConfig(max_rounds=2, exit_field="all_sections_detailed", counter_field="questioning_count"),
            LoopConfig(
                max_rounds=2, exit_field="needs_section_improvement",
                counter_field="section_improve_count",
                convergence_field="prev_section_avg_score", convergence_threshold=0.3,
            ),
        ],
    ),
    Layer(
        name="enhancement",
        description="内容增强层",
        nodes=["coder_and_artist"],
        agents=["CoderAgent", "ArtistAgent"],
        required_inputs=["sections", "outline"],
        outputs=["code_blocks", "images", "section_images"],
        criticality=Criticality.LOW,
        parallel_groups=[["CoderAgent", "ArtistAgent"]],
    ),
    Layer(
        name="validate",
        description="一致性验证层",
        nodes=["consistency_check"],
        agents=["ThreadCheckerAgent", "VoiceCheckerAgent"],
        required_inputs=["sections"],
        outputs=["thread_issues", "voice_issues"],
        criticality=Criticality.LOW,
        parallel_groups=[["ThreadCheckerAgent", "VoiceCheckerAgent"]],
        style_switches={
            "ThreadCheckerAgent": "enable_thread_check",
            "VoiceCheckerAgent": "enable_voice_check",
        },
    ),
    Layer(
        name="quality",
        description="质量控制层",
        nodes=["reviewer", "revision", "factcheck", "text_cleanup", "humanizer"],
        agents=["ReviewerAgent", "WriterAgent", "FactCheckAgent", "HumanizerAgent"],
        required_inputs=["sections", "outline"],
        optional_inputs=["thread_issues", "voice_issues", "code_blocks", "images"],
        outputs=["review_score", "review_issues", "review_approved", "revision_count"],
        criticality=Criticality.LOW,
        loops=[
            LoopConfig(max_rounds=5, exit_field="review_approved", counter_field="revision_count"),
        ],
        style_switches={
            "FactCheckAgent": "enable_fact_check",
            "text_cleanup": "enable_text_cleanup",
            "HumanizerAgent": "enable_humanizer",
        },
    ),
    Layer(
        name="output",
        description="文档输出层",
        nodes=["assembler", "summary_generator"],
        agents=["AssemblerAgent", "SummaryGeneratorAgent"],
        required_inputs=["sections", "outline"],
        optional_inputs=["code_blocks", "images", "section_images", "review_score"],
        outputs=["final_markdown", "seo_keywords", "social_summary", "meta_description"],
        criticality=Criticality.HIGH,
        style_switches={
            "SummaryGeneratorAgent": "enable_summary_gen",
        },
    ),
]


# ==================== LayerValidator ====================

class LayerValidator:
    """层间数据契约校验器"""

    def __init__(self, layers: List[Layer]):
        self.layers = layers
        self._layer_map = {l.name: l for l in layers}

    def validate_inputs(self, layer_name: str, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        layer = self._layer_map.get(layer_name)
        if not layer:
            return False, [f"未知的层: {layer_name}"]
        missing = []
        for f in layer.required_inputs:
            v = state.get(f)
            if v is None or (isinstance(v, (list, str)) and len(v) == 0):
                missing.append(f)
        return (len(missing) == 0, missing)

    def validate_outputs(self, layer_name: str, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        layer = self._layer_map.get(layer_name)
        if not layer:
            return False, [f"未知的层: {layer_name}"]
        missing = [f for f in layer.outputs if state.get(f) is None]
        return (len(missing) == 0, missing)

    def get_data_lineage(self, field_name: str) -> Dict[str, Any]:
        producer = None
        consumers: List[Dict[str, Any]] = []
        for layer in self.layers:
            if field_name in layer.outputs:
                producer = layer.name
            if field_name in layer.required_inputs or field_name in layer.optional_inputs:
                consumers.append({
                    "layer": layer.name,
                    "required": field_name in layer.required_inputs,
                })
        return {"field": field_name, "producer": producer, "consumers": consumers}
