"""TDD 测试 — 1003.15 研究预设系统"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.research_presets import (
    ResearchPreset, RESEARCH_PRESETS, get_research_preset,
    get_preset_names, apply_preset_to_state,
)

class TestResearchPreset:
    def test_four_presets_exist(self):
        assert len(RESEARCH_PRESETS) == 4
        assert set(get_preset_names()) == {"quick", "medium", "deep", "auto"}

    def test_quick_preset_values(self):
        p = get_research_preset("quick")
        assert p.max_search_count == 1
        assert p.deep_research_max_rounds == 1
        assert p.depth_requirement == "minimal"
        assert p.iteration_mode == "fixed"

    def test_deep_preset_values(self):
        p = get_research_preset("deep")
        assert p.max_search_count == 8
        assert p.deep_research_max_rounds == 4
        assert p.depth_requirement == "deep"

    def test_auto_preset_flexible(self):
        p = get_research_preset("auto")
        assert p.iteration_mode == "flexible"

    def test_get_nonexistent_returns_none(self):
        assert get_research_preset("nonexistent") is None

    def test_apply_preset_to_state(self):
        state = {"max_search_count": 2, "topic": "test"}
        result = apply_preset_to_state(state, "deep")
        assert result["max_search_count"] == 8
        assert result["research_preset_name"] == "deep"
        assert result["iteration_mode"] == "fixed"
        assert result["topic"] == "test"

    def test_apply_nonexistent_preset_noop(self):
        state = {"max_search_count": 2}
        result = apply_preset_to_state(state, "nope")
        assert result["max_search_count"] == 2

    def test_preset_descriptions_nonempty(self):
        for name, preset in RESEARCH_PRESETS.items():
            assert preset.description, f"Empty description for {name}"

    def test_preset_is_dataclass(self):
        p = get_research_preset("medium")
        assert isinstance(p, ResearchPreset)
