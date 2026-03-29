"""
37.12 博客生成分层架构 — 单元测试
"""
import json
import os
import pytest
import tempfile

from services.blog_generator.orchestrator.layer_definitions import (
    Layer, LoopConfig, Criticality, BLOG_LAYERS, LayerValidator,
)


# ==================== Layer Definitions ====================

class TestLayerDefinitions:
    """7 层流水线定义"""

    def test_seven_layers_defined(self):
        assert len(BLOG_LAYERS) == 7

    def test_layer_names(self):
        names = [l.name for l in BLOG_LAYERS]
        assert names == [
            "research", "structure", "content",
            "enhancement", "validate", "quality", "output",
        ]

    def test_critical_layers(self):
        critical = [l.name for l in BLOG_LAYERS if l.is_critical]
        assert set(critical) == {"structure", "content", "output"}

    def test_content_layer_has_three_loops(self):
        content = next(l for l in BLOG_LAYERS if l.name == "content")
        assert len(content.loops) == 3

    def test_total_nodes_is_19(self):
        total = sum(len(l.nodes) for l in BLOG_LAYERS)
        assert total == 19

    def test_enhancement_layer_has_parallel(self):
        enh = next(l for l in BLOG_LAYERS if l.name == "enhancement")
        assert len(enh.parallel_groups) == 1


# ==================== LayerValidator ====================

class TestLayerValidator:
    """层间契约校验"""

    def setup_method(self):
        self.validator = LayerValidator(BLOG_LAYERS)

    def test_validate_inputs_success(self):
        state = {"topic": "AI", "article_type": "tech", "target_audience": "dev"}
        ok, missing = self.validator.validate_inputs("research", state)
        assert ok is True
        assert missing == []

    def test_validate_inputs_missing(self):
        state = {"topic": "AI"}
        ok, missing = self.validator.validate_inputs("research", state)
        assert ok is False
        assert "article_type" in missing

    def test_validate_outputs(self):
        state = {
            "search_results": [{"title": "x"}],
            "background_knowledge": "bg",
            "key_concepts": ["a"],
            "reference_links": ["http://x"],
        }
        ok, missing = self.validator.validate_outputs("research", state)
        assert ok is True

    def test_validate_unknown_layer(self):
        ok, errors = self.validator.validate_inputs("nonexistent", {})
        assert ok is False

    def test_data_lineage(self):
        lineage = self.validator.get_data_lineage("outline")
        assert lineage["producer"] == "structure"
        assert any(c["layer"] == "content" for c in lineage["consumers"])


# ==================== YAML → JSON Migration ====================

class TestMigrateYamlToJson:
    """YAML → JSON 迁移工具"""

    def test_migrate_medium_preset(self):
        from services.blog_generator.orchestrator.migrate_yaml_to_json import (
            migrate_yaml_to_json,
        )
        yaml_path = os.path.join(
            os.path.dirname(__file__), "..",
            "services", "blog_generator", "workflow_configs", "medium.yaml",
        )
        result = migrate_yaml_to_json(yaml_path)
        assert result["name"] == "medium"
        assert "default_style" in result
        assert "phases" in result
        assert isinstance(result["phases"], dict)

    def test_migrate_agent_registry(self):
        from services.blog_generator.orchestrator.migrate_yaml_to_json import (
            migrate_yaml_to_json,
        )
        yaml_path = os.path.join(
            os.path.dirname(__file__), "..",
            "services", "blog_generator", "workflow_configs", "agent_registry.yaml",
        )
        result = migrate_yaml_to_json(yaml_path)
        assert "agents" in result

    def test_migrate_all_presets(self):
        from services.blog_generator.orchestrator.migrate_yaml_to_json import (
            migrate_all_presets,
        )
        configs_dir = os.path.join(
            os.path.dirname(__file__), "..",
            "services", "blog_generator", "workflow_configs",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            results = migrate_all_presets(configs_dir, tmpdir)
            assert len(results) >= 6  # 6 presets + agent_registry
            # 验证输出文件存在
            for name in results:
                json_path = os.path.join(tmpdir, f"{name}.json")
                assert os.path.exists(json_path)


# ==================== JSON Schema Validation ====================

class TestWorkflowSchema:
    """JSON Schema 校验"""

    def test_valid_config(self):
        from services.blog_generator.orchestrator.workflow_schema import (
            validate_workflow_config,
        )
        config = {
            "name": "test",
            "phases": {"plan": ["researcher", "planner"]},
        }
        errors = validate_workflow_config(config)
        assert errors == []

    def test_missing_name(self):
        from services.blog_generator.orchestrator.workflow_schema import (
            validate_workflow_config,
        )
        config = {"phases": {"plan": ["researcher"]}}
        errors = validate_workflow_config(config)
        assert len(errors) > 0

    def test_invalid_phases_type(self):
        from services.blog_generator.orchestrator.workflow_schema import (
            validate_workflow_config,
        )
        config = {"name": "test", "phases": "not_a_dict"}
        errors = validate_workflow_config(config)
        assert len(errors) > 0


# ==================== DeclarativeEngine ====================

class TestDeclarativeEngine:
    """声明式编排引擎"""

    def test_validate_config_valid(self):
        from services.blog_generator.orchestrator.declarative_engine import (
            DeclarativeEngine,
        )
        config = {
            "name": "test",
            "phases": {"plan": ["researcher", "planner"]},
        }
        engine = DeclarativeEngine(config)
        errors = engine.validate_config()
        assert errors == []

    def test_resolve_extends(self):
        from services.blog_generator.orchestrator.declarative_engine import (
            DeclarativeEngine,
        )
        parent = {
            "name": "parent",
            "default_style": {"max_revision_rounds": 3, "tone": "formal"},
            "phases": {"plan": ["researcher"], "write": ["writer"]},
        }
        child = {
            "name": "child",
            "extends": "parent",
            "default_style": {"tone": "casual"},
            "phases": {"write": ["writer", "questioner"]},
        }
        engine = DeclarativeEngine(child)
        merged = engine.resolve_extends({"parent": parent})
        assert merged["name"] == "child"
        assert merged["default_style"]["max_revision_rounds"] == 3
        assert merged["default_style"]["tone"] == "casual"
        assert merged["phases"]["plan"] == ["researcher"]
        assert merged["phases"]["write"] == ["writer", "questioner"]

    def test_resolve_style_refs(self):
        from services.blog_generator.orchestrator.declarative_engine import (
            resolve_style_refs,
        )
        config = {
            "loop": {
                "max_rounds": "$style.max_revision_rounds",
                "exit_when": "review_approved",
            }
        }
        style = {"max_revision_rounds": 5}
        resolved = resolve_style_refs(config, style)
        assert resolved["loop"]["max_rounds"] == 5

    def test_resolve_no_extends(self):
        from services.blog_generator.orchestrator.declarative_engine import (
            DeclarativeEngine,
        )
        config = {"name": "standalone", "phases": {"plan": ["researcher"]}}
        engine = DeclarativeEngine(config)
        merged = engine.resolve_extends({})
        assert merged["name"] == "standalone"
