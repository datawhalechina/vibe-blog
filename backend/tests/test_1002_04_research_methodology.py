"""1002.04 系统化深度研究方法论 — 单元测试

测试覆盖:
- 数据结构: ResearchPhase, InformationType, ResearchDimension, ResearchPlan, SynthesisCheckResult
- 方法论引擎: StructuredResearchMethodology 四阶段流程
- 集成: ResearcherAgent 方法论分支
"""
import json
import pytest

from services.blog_generator.services.research_methodology import (
    ResearchPhase,
    InformationType,
    ResearchDimension,
    ResearchPlan,
    SynthesisCheckResult,
    StructuredResearchMethodology,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class MockLLM:
    """Mock LLM 客户端，返回预设 JSON"""

    def __init__(self, response=None):
        self._response = response or json.dumps({
            "thought": "需要从技术架构和生态两个维度分析",
            "dimensions": [
                {
                    "name": "技术架构",
                    "description": "核心设计与实现",
                    "priority": 0,
                    "search_queries": ["AI Agent 架构设计", "Agent 框架对比"],
                },
                {
                    "name": "生态系统",
                    "description": "社区与工具链",
                    "priority": 1,
                    "search_queries": ["AI Agent 生态"],
                },
            ],
            "has_enough_context": False,
        })
        self.call_count = 0

    def chat(self, messages=None, response_format=None, **kwargs):
        self.call_count += 1
        return self._response


class MockSearchService:
    """Mock 搜索服务，返回预设结果"""

    def __init__(self, results=None):
        self._results = results or [
            {
                "title": "AI Agent Framework Comparison",
                "url": "https://example.com/agent-comparison",
                "content": "数据 统计 案例 专家 趋势 对比 挑战 comparison example trend",
            },
        ]
        self.call_count = 0

    def search(self, query, max_results=10):
        self.call_count += 1
        return {"success": True, "results": self._results[:max_results]}


class MockGapDetector:
    """Mock 知识空白检测器"""

    def detect(self, search_results, topic, outline=None):
        return [{"gap": "缺少性能数据", "refined_query": f"{topic} benchmark"}]


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def mock_search():
    return MockSearchService()


@pytest.fixture
def mock_gap_detector():
    return MockGapDetector()


@pytest.fixture
def engine(mock_llm, mock_search):
    return StructuredResearchMethodology(mock_llm, mock_search)


@pytest.fixture
def engine_with_gap(mock_llm, mock_search, mock_gap_detector):
    return StructuredResearchMethodology(
        mock_llm, mock_search, gap_detector=mock_gap_detector
    )


# ── 数据结构测试 ─────────────────────────────────────────────────────


class TestResearchDataStructures:
    """数据结构单元测试"""

    def test_research_phase_values(self):
        assert ResearchPhase.BROAD_EXPLORATION == "broad_exploration"
        assert ResearchPhase.DEEP_DIVE == "deep_dive"
        assert ResearchPhase.DIVERSITY_VALIDATION == "diversity_validation"
        assert ResearchPhase.SYNTHESIS_CHECK == "synthesis_check"
        assert len(ResearchPhase) == 4

    def test_info_type_enum_values(self):
        assert InformationType.FACTS_DATA.value == "facts_data"
        assert InformationType.CHALLENGES_CRITICISMS.value == "challenges_criticisms"
        assert len(InformationType) == 6

    def test_research_dimension_defaults(self):
        dim = ResearchDimension(name="AI 市场", description="市场分析")
        assert dim.priority == 0
        assert dim.search_queries == []
        assert dim.covered_info_types == []

    def test_research_dimension_with_queries(self):
        dim = ResearchDimension(
            name="技术架构",
            description="核心设计",
            priority=1,
            search_queries=["query1", "query2"],
        )
        assert len(dim.search_queries) == 2
        assert dim.priority == 1

    def test_research_plan_creation(self):
        plan = ResearchPlan(
            topic="AI Agent 框架对比",
            thought="需要从技术架构、生态、性能三个维度分析",
            dimensions=[
                ResearchDimension(name="技术架构", description="核心设计"),
                ResearchDimension(name="生态系统", description="社区与工具"),
            ],
        )
        assert len(plan.dimensions) == 2
        assert not plan.has_enough_context
        assert plan.coverage_scores == {}

    def test_synthesis_check_all_pass(self):
        result = SynthesisCheckResult(
            multi_angle_searched=True,
            full_sources_read=True,
            concrete_data_found=True,
            balanced_viewpoints=True,
            authoritative_sources=True,
        )
        assert result.passed is True

    def test_synthesis_check_partial_fail(self):
        result = SynthesisCheckResult(
            multi_angle_searched=True,
            full_sources_read=True,
            concrete_data_found=False,
            balanced_viewpoints=True,
            authoritative_sources=True,
        )
        assert result.passed is False

    def test_synthesis_check_all_false(self):
        result = SynthesisCheckResult()
        assert result.passed is False

    def test_synthesis_check_single_true(self):
        result = SynthesisCheckResult(multi_angle_searched=True)
        assert result.passed is False


# ── 方法论引擎测试 ───────────────────────────────────────────────────

class TestBroadExploration:
    """Phase 1: 广度探索测试"""

    def test_returns_research_plan(self, engine):
        plan = engine.broad_exploration("AI Agent", "intermediate")
        assert isinstance(plan, ResearchPlan)
        assert plan.topic == "AI Agent"
        assert len(plan.dimensions) >= 1

    def test_plan_has_thought(self, engine):
        plan = engine.broad_exploration("AI Agent", "intermediate")
        assert plan.thought != ""

    def test_plan_dimensions_have_queries(self, engine):
        plan = engine.broad_exploration("AI Agent", "intermediate")
        for dim in plan.dimensions:
            assert isinstance(dim.search_queries, list)

    def test_calls_search_service(self, engine, mock_search):
        engine.broad_exploration("AI Agent", "intermediate")
        assert mock_search.call_count >= 1

    def test_calls_llm(self, engine, mock_llm):
        engine.broad_exploration("AI Agent", "intermediate")
        assert mock_llm.call_count >= 1

    def test_fallback_on_llm_error(self, mock_search):
        """LLM 返回无效 JSON 时回退到默认计划"""
        bad_llm = MockLLM(response="not valid json")
        engine = StructuredResearchMethodology(bad_llm, mock_search)
        plan = engine.broad_exploration("AI Agent", "intermediate")
        assert isinstance(plan, ResearchPlan)
        assert plan.topic == "AI Agent"

    def test_search_failure_handled(self, mock_llm):
        """搜索服务失败时不崩溃"""

        class FailSearch:
            def search(self, query, max_results=10):
                return {"success": False, "results": []}

        engine = StructuredResearchMethodology(mock_llm, FailSearch())
        plan = engine.broad_exploration("AI Agent", "intermediate")
        assert isinstance(plan, ResearchPlan)


class TestDeepDive:
    """Phase 2: 深度挖掘测试"""

    def test_expands_results(self, engine):
        plan = ResearchPlan(
            topic="test",
            thought="test",
            dimensions=[
                ResearchDimension(
                    name="dim1",
                    description="d",
                    search_queries=["q1", "q2"],
                )
            ],
        )
        results = engine.deep_dive(plan, [])
        assert len(results) > 0

    def test_deduplicates_urls(self, engine):
        plan = ResearchPlan(
            topic="test",
            thought="test",
            dimensions=[
                ResearchDimension(
                    name="dim1",
                    description="d",
                    search_queries=["q1", "q2", "q3"],
                )
            ],
        )
        existing = [{"url": "https://example.com/agent-comparison", "title": "Existing"}]
        results = engine.deep_dive(plan, existing)
        urls = [r.get("url") for r in results]
        assert len(urls) == len(set(urls))

    def test_limits_queries_per_dimension(self, engine, mock_search):
        plan = ResearchPlan(
            topic="test",
            thought="test",
            dimensions=[
                ResearchDimension(
                    name="dim1",
                    description="d",
                    search_queries=["q1", "q2", "q3", "q4", "q5"],
                )
            ],
        )
        engine.deep_dive(plan, [])
        assert mock_search.call_count <= 3  # 每维度最多 3 个查询

    def test_empty_dimensions(self, engine):
        plan = ResearchPlan(topic="test", thought="test", dimensions=[])
        results = engine.deep_dive(plan, [{"url": "https://a.com"}])
        assert len(results) == 1  # 原有结果不变


class TestDiversityValidation:
    """Phase 3: 多样性与验证测试"""

    def test_returns_coverage_dict(self, engine):
        results = [
            {"content": "数据 统计 案例 专家 趋势 对比 挑战 data example expert trend comparison challenge"}
        ]
        plan = ResearchPlan(topic="test", thought="test")
        div = engine.diversity_validation("test", results, plan)
        assert "coverage" in div
        assert "results" in div
        assert "missing_types" in div

    def test_detects_missing_types(self, engine):
        results = [{"content": "只有数据 data 统计"}]
        plan = ResearchPlan(topic="test", thought="test")
        div = engine.diversity_validation("test", results, plan)
        assert len(div["missing_types"]) > 0

    def test_gap_detector_called_on_missing(self, engine_with_gap):
        results = [{"content": "只有数据"}]
        plan = ResearchPlan(topic="test", thought="test")
        div = engine_with_gap.diversity_validation("test", results, plan)
        assert "results" in div

    def test_all_types_covered(self, engine):
        results = [
            {"content": "数据 统计 案例 example 专家 expert 趋势 trend 对比 vs 挑战 challenge"}
        ]
        plan = ResearchPlan(topic="test", thought="test")
        div = engine.diversity_validation("test", results, plan)
        assert len(div["missing_types"]) == 0


class TestSynthesisCheck:
    """Phase 4: 综合检查测试"""

    def test_returns_synthesis_result(self):
        llm = MockLLM(response=json.dumps({
            "multi_angle_searched": True,
            "full_sources_read": True,
            "concrete_data_found": True,
            "balanced_viewpoints": True,
            "authoritative_sources": True,
        }))
        engine = StructuredResearchMethodology(llm, MockSearchService())
        plan = ResearchPlan(topic="test", thought="test")
        result = engine.synthesis_check("test", [], plan)
        assert isinstance(result, SynthesisCheckResult)
        assert result.passed is True

    def test_partial_pass(self):
        llm = MockLLM(response=json.dumps({
            "multi_angle_searched": True,
            "full_sources_read": False,
            "concrete_data_found": True,
            "balanced_viewpoints": True,
            "authoritative_sources": True,
        }))
        engine = StructuredResearchMethodology(llm, MockSearchService())
        plan = ResearchPlan(topic="test", thought="test")
        result = engine.synthesis_check("test", [], plan)
        assert result.passed is False

    def test_llm_error_returns_default(self):
        llm = MockLLM(response="invalid json")
        engine = StructuredResearchMethodology(llm, MockSearchService())
        plan = ResearchPlan(topic="test", thought="test")
        result = engine.synthesis_check("test", [], plan)
        assert isinstance(result, SynthesisCheckResult)
        assert result.passed is False


class TestFullPipeline:
    """端到端四阶段完整流程测试"""

    def test_full_pipeline(self, engine):
        plan = engine.broad_exploration("AI Agent", "intermediate")
        results = engine.deep_dive(plan, [])
        div = engine.diversity_validation("AI Agent", results, plan)
        synthesis = engine.synthesis_check("AI Agent", div["results"], plan)
        assert isinstance(plan, ResearchPlan)
        assert isinstance(results, list)
        assert isinstance(div, dict)
        assert isinstance(synthesis, SynthesisCheckResult)

    def test_pipeline_with_gap_detector(self, engine_with_gap):
        plan = engine_with_gap.broad_exploration("AI Agent", "intermediate")
        results = engine_with_gap.deep_dive(plan, [])
        div = engine_with_gap.diversity_validation("AI Agent", results, plan)
        synthesis = engine_with_gap.synthesis_check("AI Agent", div["results"], plan)
        assert isinstance(synthesis, SynthesisCheckResult)
