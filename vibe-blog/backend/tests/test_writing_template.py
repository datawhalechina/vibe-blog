"""
37.13 写作模板体系与风格学习 — 单元测试
"""
import json
import os
import shutil
import tempfile
import pytest

from services.blog_generator.orchestrator.template_loader import TemplateLoader
from services.blog_generator.orchestrator.style_loader import StyleLoader
from services.blog_generator.orchestrator.prompt_composer import PromptComposer


# ---------------------------------------------------------------------------
# TemplateLoader
# ---------------------------------------------------------------------------

class TestTemplateLoader:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.loader = TemplateLoader(templates_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, name: str, data: dict):
        with open(os.path.join(self.tmpdir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _minimal_template(self, name="test", builtin=False):
        return {
            "name": name,
            "display_name": f"Test {name}",
            "description": "A test template",
            "builtin": builtin,
            "structure": {
                "opening": {"mode": "question", "description": "open"},
                "body": {
                    "mode": "tutorial",
                    "section_template": [],
                    "transition": "none",
                    "min_sections": 2,
                    "max_sections": 6,
                },
                "closing": {"mode": "summary", "description": "close"},
            },
            "prompt_patches": {},
            "agent_config": {},
            "outline_schema": {},
        }

    # --- load_all / get ---

    def test_load_all_empty(self):
        result = self.loader.load_all()
        assert result == {}

    def test_load_all_finds_json(self):
        self._write("alpha", self._minimal_template("alpha"))
        result = self.loader.load_all()
        assert "alpha" in result

    def test_get_returns_template(self):
        self._write("beta", self._minimal_template("beta"))
        self.loader.load_all()
        t = self.loader.get("beta")
        assert t is not None
        assert t["name"] == "beta"

    def test_get_missing_returns_none(self):
        self.loader.load_all()
        assert self.loader.get("nonexistent") is None

    # --- save ---

    def test_save_creates_file(self):
        tpl = self._minimal_template("saved")
        self.loader.save(tpl)
        assert os.path.exists(os.path.join(self.tmpdir, "saved.json"))
        self.loader.load_all()
        assert self.loader.get("saved") is not None

    def test_save_invalid_missing_name(self):
        tpl = {"display_name": "no name"}
        with pytest.raises(ValueError):
            self.loader.save(tpl)

    # --- delete ---

    def test_delete_custom(self):
        tpl = self._minimal_template("deleteme")
        self.loader.save(tpl)
        assert self.loader.delete("deleteme") is True
        assert not os.path.exists(os.path.join(self.tmpdir, "deleteme.json"))

    def test_delete_builtin_rejected(self):
        tpl = self._minimal_template("builtin_one", builtin=True)
        self.loader.save(tpl)
        self.loader.load_all()
        with pytest.raises(PermissionError):
            self.loader.delete("builtin_one")

    def test_delete_nonexistent(self):
        assert self.loader.delete("ghost") is False


# ---------------------------------------------------------------------------
# StyleLoader
# ---------------------------------------------------------------------------

class TestStyleLoader:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.loader = StyleLoader(styles_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, name: str, data: dict):
        with open(os.path.join(self.tmpdir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _minimal_style(self, name="test_style", builtin=False):
        return {
            "name": name,
            "display_name": f"Test {name}",
            "description": "A test style",
            "builtin": builtin,
            "tone": "professional",
            "style_guide": "Write professionally.",
        }

    def test_load_all_and_get(self):
        self._write("s1", self._minimal_style("s1"))
        result = self.loader.load_all()
        assert "s1" in result
        assert self.loader.get("s1")["tone"] == "professional"

    def test_save_and_load(self):
        style = self._minimal_style("new_style")
        self.loader.save(style)
        self.loader.load_all()
        assert self.loader.get("new_style") is not None

    def test_save_invalid_missing_name(self):
        with pytest.raises(ValueError):
            self.loader.save({"tone": "casual"})

    def test_delete_custom(self):
        self.loader.save(self._minimal_style("del_me"))
        assert self.loader.delete("del_me") is True

    def test_delete_builtin_rejected(self):
        self.loader.save(self._minimal_style("builtin_s", builtin=True))
        self.loader.load_all()
        with pytest.raises(PermissionError):
            self.loader.delete("builtin_s")


# ---------------------------------------------------------------------------
# PromptComposer
# ---------------------------------------------------------------------------

class TestPromptComposer:

    def test_compose_no_template_no_style(self):
        """无模板无风格 → 仅返回基础 prompt"""
        composer = PromptComposer()
        result = composer.compose(
            agent_name="writer",
            base_prompt="你是一位技术博客作者。",
        )
        assert "你是一位技术博客作者" in result
        assert "写作结构要求" not in result
        assert "写作风格要求" not in result

    def test_compose_with_template_patch(self):
        """有模板补丁 → 注入模板指令"""
        template = {
            "prompt_patches": {
                "writer": "每章先描述痛点再给方案。",
            }
        }
        composer = PromptComposer()
        result = composer.compose(
            agent_name="writer",
            base_prompt="你是一位技术博客作者。",
            template=template,
        )
        assert "每章先描述痛点再给方案" in result
        assert "写作结构要求" in result

    def test_compose_with_style_guide(self):
        """有风格指南 → 注入风格指令"""
        style = {"style_guide": "用口语化的语言写作。"}
        composer = PromptComposer()
        result = composer.compose(
            agent_name="writer",
            base_prompt="你是一位技术博客作者。",
            style=style,
        )
        assert "用口语化的语言写作" in result
        assert "写作风格要求" in result

    def test_compose_with_both(self):
        """模板 + 风格 → 都注入"""
        template = {"prompt_patches": {"planner": "大纲要求..."}}
        style = {"style_guide": "学术风格。"}
        composer = PromptComposer()
        result = composer.compose(
            agent_name="planner",
            base_prompt="你是大纲规划师。",
            template=template,
            style=style,
        )
        assert "大纲要求" in result
        assert "学术风格" in result

    def test_compose_agent_not_in_patches(self):
        """模板中无该 Agent 的补丁 → 跳过模板注入"""
        template = {"prompt_patches": {"writer": "writer only"}}
        composer = PromptComposer()
        result = composer.compose(
            agent_name="reviewer",
            base_prompt="你是审核员。",
            template=template,
        )
        assert "writer only" not in result
        assert "写作结构要求" not in result

    def test_compose_appends_runtime_params(self):
        """运行时参数附加到末尾"""
        composer = PromptComposer()
        result = composer.compose(
            agent_name="writer",
            base_prompt="基础。",
            runtime_context="## 任务\n写第一章。",
        )
        assert "写第一章" in result


# ---------------------------------------------------------------------------
# Preset files existence (integration-level)
# ---------------------------------------------------------------------------

class TestPresetFiles:
    """验证预置模板和风格 JSON 文件存在且可解析"""

    BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
    TEMPLATES_DIR = os.path.join(BACKEND_DIR, "workflow_configs", "templates")
    STYLES_DIR = os.path.join(BACKEND_DIR, "workflow_configs", "styles")

    EXPECTED_TEMPLATES = [
        "problem_solution", "tutorial", "comparison",
        "narrative", "deep_analysis", "checklist",
    ]
    EXPECTED_STYLES = [
        "casual", "professional", "academic",
        "humorous", "storytelling", "concise",
    ]

    def test_all_preset_templates_exist(self):
        for name in self.EXPECTED_TEMPLATES:
            path = os.path.join(self.TEMPLATES_DIR, f"{name}.json")
            assert os.path.exists(path), f"预置模板缺失: {name}.json"
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("name") == name
            assert data.get("builtin") is True

    def test_all_preset_styles_exist(self):
        for name in self.EXPECTED_STYLES:
            path = os.path.join(self.STYLES_DIR, f"{name}.json")
            assert os.path.exists(path), f"预置风格缺失: {name}.json"
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("name") == name
            assert data.get("builtin") is True

    def test_template_loader_loads_presets(self):
        if not os.path.isdir(self.TEMPLATES_DIR):
            pytest.skip("templates dir not yet created")
        loader = TemplateLoader(templates_dir=self.TEMPLATES_DIR)
        all_t = loader.load_all()
        for name in self.EXPECTED_TEMPLATES:
            assert name in all_t, f"TemplateLoader 未加载预置模板: {name}"

    def test_style_loader_loads_presets(self):
        if not os.path.isdir(self.STYLES_DIR):
            pytest.skip("styles dir not yet created")
        loader = StyleLoader(styles_dir=self.STYLES_DIR)
        all_s = loader.load_all()
        for name in self.EXPECTED_STYLES:
            assert name in all_s, f"StyleLoader 未加载预置风格: {name}"
