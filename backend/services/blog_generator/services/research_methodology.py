"""
系统化深度研究方法论引擎

融合四阶段结构化研究方法论与 vibe-blog 现有搜索体系:
  Phase 1: Broad Exploration  — 广度探索，识别研究维度
  Phase 2: Deep Dive          — 深度挖掘，定向搜索
  Phase 3: Diversity Validation — 多样性验证，六维信息类型覆盖
  Phase 4: Synthesis Check    — 综合检查，五项自检清单

环境变量:
  STRUCTURED_RESEARCH_ENABLED: 总开关 (default: false)
"""
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── 枚举 & 数据结构 ──────────────────────────────────────────────────


class ResearchPhase(str, Enum):
    """研究阶段枚举"""
    BROAD_EXPLORATION = "broad_exploration"
    DEEP_DIVE = "deep_dive"
    DIVERSITY_VALIDATION = "diversity_validation"
    SYNTHESIS_CHECK = "synthesis_check"


class InformationType(str, Enum):
    """六维信息类型"""
    FACTS_DATA = "facts_data"
    EXAMPLES_CASES = "examples_cases"
    EXPERT_OPINIONS = "expert_opinions"
    TRENDS_PREDICTIONS = "trends_predictions"
    COMPARISONS = "comparisons"
    CHALLENGES_CRITICISMS = "challenges_criticisms"


@dataclass
class ResearchDimension:
    """研究维度"""
    name: str
    description: str
    priority: int = 0
    search_queries: List[str] = field(default_factory=list)
    covered_info_types: List[InformationType] = field(default_factory=list)

@dataclass
class ResearchPlan:
    """结构化研究计划"""
    topic: str
    thought: str
    dimensions: List[ResearchDimension] = field(default_factory=list)
    has_enough_context: bool = False
    coverage_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class SynthesisCheckResult:
    """Phase 4 综合检查结果"""
    multi_angle_searched: bool = False
    full_sources_read: bool = False
    concrete_data_found: bool = False
    balanced_viewpoints: bool = False
    authoritative_sources: bool = False

    @property
    def passed(self) -> bool:
        return all([
            self.multi_angle_searched,
            self.full_sources_read,
            self.concrete_data_found,
            self.balanced_viewpoints,
            self.authoritative_sources,
        ])


# ── 方法论引擎 ───────────────────────────────────────────────────────


class StructuredResearchMethodology:
    """
    系统化深度研究方法论引擎

    在 SmartSearchService / DeepResearchEngine 之上提供结构化研究流程编排，
    不替换底层搜索实现。
    """

    def __init__(self, llm_client, search_service,
                 deep_research_engine=None, gap_detector=None):
        self.llm = llm_client
        self.search_service = search_service
        self.deep_research_engine = deep_research_engine
        self.gap_detector = gap_detector

    # ── Phase 1: Broad Exploration ────────────────────────────────────

    def broad_exploration(self, topic: str, target_audience: str) -> ResearchPlan:
        """Phase 1: 广度探索 — 初始搜索 + LLM 识别研究维度"""
        logger.info(f"[Phase 1] Broad Exploration: {topic}")

        initial_results = self._safe_search(topic, max_results=10)

        prompt = self._build_dimension_prompt(topic, target_audience, initial_results)
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            plan = self._parse_research_plan(topic, response)
        except Exception as e:
            logger.warning(f"[Phase 1] LLM 分析失败: {e}")
            plan = ResearchPlan(topic=topic, thought="LLM 分析失败，使用默认计划")

        logger.info(f"[Phase 1] 识别 {len(plan.dimensions)} 个研究维度")
        return plan

    # ── Phase 2: Deep Dive ────────────────────────────────────────────

    def deep_dive(self, plan: ResearchPlan, all_results: List[Dict]) -> List[Dict]:
        """Phase 2: 深度挖掘 — 对每个维度执行定向搜索"""
        logger.info(f"[Phase 2] Deep Dive: {len(plan.dimensions)} 维度")

        seen = {r.get("url") for r in all_results if r.get("url")}
        for dim in plan.dimensions:
            for query in dim.search_queries[:3]:
                new_items = self._safe_search(query, max_results=5)
                for item in new_items:
                    url = item.get("url")
                    if url and url not in seen:
                        all_results.append(item)
                        seen.add(url)

        logger.info(f"[Phase 2] 累计 {len(all_results)} 条结果")
        return all_results

    # ── Phase 3: Diversity & Validation ───────────────────────────────

    def diversity_validation(self, topic: str, all_results: List[Dict],
                             plan: ResearchPlan) -> Dict[str, Any]:
        """Phase 3: 多样性与验证 — 六维信息类型覆盖检查"""
        logger.info("[Phase 3] Diversity & Validation")

        coverage = self._check_info_type_coverage(all_results)
        missing_types = [t for t, covered in coverage.items() if not covered]

        if missing_types and self.gap_detector:
            try:
                gaps = self.gap_detector.detect(all_results, topic)
                for gap in (gaps or [])[:3]:
                    query = gap.get("refined_query", "")
                    if query:
                        new_items = self._safe_search(query, max_results=5)
                        all_results.extend(new_items)
            except Exception as e:
                logger.warning(f"[Phase 3] 缺口补充失败: {e}")

        return {
            "results": all_results,
            "coverage": coverage,
            "missing_types": missing_types,
        }

    # ── Phase 4: Synthesis Check ──────────────────────────────────────

    def synthesis_check(self, topic: str, all_results: List[Dict],
                        plan: ResearchPlan) -> SynthesisCheckResult:
        """Phase 4: 综合检查 — 五项自检清单"""
        logger.info("[Phase 4] Synthesis Check")

        prompt = self._build_synthesis_prompt(topic, all_results, plan)
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return self._parse_synthesis_result(response)
        except Exception as e:
            logger.warning(f"[Phase 4] 综合检查失败: {e}")
            return SynthesisCheckResult()

    # ── 内部辅助 ──────────────────────────────────────────────────────

    def _safe_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """安全搜索封装，失败返回空列表"""
        try:
            result = self.search_service.search(query, max_results=max_results)
            if result.get("success"):
                return result.get("results", [])
        except Exception as e:
            logger.warning(f"搜索失败 [{query}]: {e}")
        return []

    def _build_dimension_prompt(self, topic, audience, results):
        summaries = "\n".join(
            f"- {r.get('title', '')}: {(r.get('content', '') or '')[:200]}"
            for r in results[:10]
        )
        return (
            f"分析以下关于「{topic}」的初始搜索结果，识别需要深入研究的维度。\n"
            f"目标受众: {audience}\n\n"
            f"初始搜索结果:\n{summaries}\n\n"
            f'输出 JSON:\n'
            f'{{"thought": "研究思路", "dimensions": ['
            f'{{"name": "维度名", "description": "描述", "priority": 0, '
            f'"search_queries": ["查询1", "查询2"]}}], '
            f'"has_enough_context": false}}'
        )

    def _build_synthesis_prompt(self, topic, results, plan):
        return (
            f"评估关于「{topic}」的研究是否充分。\n"
            f"研究维度: {len(plan.dimensions)} 个\n"
            f"搜索结果: {len(results)} 条\n\n"
            f'输出 JSON:\n'
            f'{{"multi_angle_searched": true, "full_sources_read": true, '
            f'"concrete_data_found": true, "balanced_viewpoints": true, '
            f'"authoritative_sources": true}}'
        )

    def _parse_research_plan(self, topic: str, response: str) -> ResearchPlan:
        try:
            data = json.loads(response) if isinstance(response, str) else response
            dims = []
            for d in data.get("dimensions", []):
                dims.append(ResearchDimension(
                    name=d.get("name", ""),
                    description=d.get("description", ""),
                    priority=d.get("priority", 0),
                    search_queries=d.get("search_queries", []),
                ))
            return ResearchPlan(
                topic=topic,
                thought=data.get("thought", ""),
                dimensions=dims,
                has_enough_context=data.get("has_enough_context", False),
            )
        except Exception as e:
            logger.warning(f"研究计划解析失败: {e}")
            return ResearchPlan(topic=topic, thought="解析失败，使用默认计划")

    def _check_info_type_coverage(self, results: List[Dict]) -> Dict[InformationType, bool]:
        """基于关键词检测六维信息类型覆盖"""
        content = " ".join(
            (r.get("content", "") or "")[:500] for r in results[:20]
        )
        return {
            InformationType.FACTS_DATA: any(
                k in content for k in ["数据", "统计", "data", "%"]
            ),
            InformationType.EXAMPLES_CASES: any(
                k in content for k in ["案例", "example", "case"]
            ),
            InformationType.EXPERT_OPINIONS: any(
                k in content for k in ["专家", "expert", "分析师"]
            ),
            InformationType.TRENDS_PREDICTIONS: any(
                k in content for k in ["趋势", "trend", "预测"]
            ),
            InformationType.COMPARISONS: any(
                k in content for k in ["对比", "vs", "comparison"]
            ),
            InformationType.CHALLENGES_CRITICISMS: any(
                k in content for k in ["挑战", "challenge", "limitation"]
            ),
        }

    def _parse_synthesis_result(self, response: str) -> SynthesisCheckResult:
        try:
            data = json.loads(response) if isinstance(response, str) else response
            return SynthesisCheckResult(**{
                k: data.get(k, False)
                for k in [
                    "multi_angle_searched", "full_sources_read",
                    "concrete_data_found", "balanced_viewpoints",
                    "authoritative_sources",
                ]
            })
        except Exception:
            return SynthesisCheckResult()
