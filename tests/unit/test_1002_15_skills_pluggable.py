"""
1002.15 Skills 可插拔系统 — 单元测试

覆盖: UnifiedSkill 数据模型、SkillsStateConfig、UnifiedSkillLoader、
       ZIP 安装、REST API、WritingSkillManager 统一模式兼容性
"""
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from services.blog_generator.skills.unified_skill import (
    SkillCategory,
    SkillSource,
    UnifiedSkill,
)
from services.blog_generator.skills.skills_state_config import SkillsStateConfig
from services.blog_generator.skills.loader import UnifiedSkillLoader
from services.blog_generator.skills.registry import SkillRegistry
from services.blog_generator.skills.writing_skill_manager import WritingSkillManager


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def skills_root(tmp_path):
    """创建临时技能目录结构"""
    # public/tech-tutorial
    (tmp_path / "public" / "tech-tutorial").mkdir(parents=True)
    (tmp_path / "public" / "tech-tutorial" / "SKILL.md").write_text(
        "---\nname: tech-tutorial\n"
        "description: 技术教程写作技能\nlicense: MIT\n"
        "allowed-tools: zhipu-search, jina-reader\n---\n\n"
        "# 技术教程\n\n## 方法论\n",
        encoding="utf-8",
    )
    # public/deep-research
    (tmp_path / "public" / "deep-research").mkdir(parents=True)
    (tmp_path / "public" / "deep-research" / "SKILL.md").write_text(
        "---\nname: deep-research\n"
        "description: 深度研究技能\nlicense: MIT\n---\n\n"
        "# 深度研究\n",
        encoding="utf-8",
    )
    # custom/my-custom
    (tmp_path / "custom" / "my-custom").mkdir(parents=True)
    (tmp_path / "custom" / "my-custom" / "SKILL.md").write_text(
        "---\nname: my-custom\ndescription: 自定义技能\n---\n\n# Custom\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前清空 SkillRegistry"""
    saved = dict(SkillRegistry._skills)
    SkillRegistry._skills.clear()
    yield
    SkillRegistry._skills.clear()
    SkillRegistry._skills.update(saved)


# ============================================================
# 1. UnifiedSkill 数据模型
# ============================================================

class TestUnifiedSkill:
    def test_declarative_defaults(self):
        s = UnifiedSkill(name="test", description="desc", source=SkillSource.DECLARATIVE)
        assert s.category == SkillCategory.PUBLIC
        assert s.enabled is True
        assert s.allowed_tools == []
        assert s.content == ""
        assert s.func is None

    def test_programmatic_fields(self):
        fn = lambda x: x
        s = UnifiedSkill(
            name="pp", description="post", source=SkillSource.PROGRAMMATIC,
            category=SkillCategory.BUILTIN, func=fn, post_process=True,
        )
        assert s.func is fn
        assert s.post_process is True

    def test_source_enum_values(self):
        assert SkillSource.DECLARATIVE.value == "declarative"
        assert SkillSource.PROGRAMMATIC.value == "programmatic"

    def test_category_enum_values(self):
        assert SkillCategory.PUBLIC.value == "public"
        assert SkillCategory.CUSTOM.value == "custom"
        assert SkillCategory.BUILTIN.value == "builtin"


# ============================================================
# 2. SkillsStateConfig
# ============================================================

class TestSkillsStateConfig:
    def test_missing_file_defaults_enabled(self, tmp_path):
        cfg = SkillsStateConfig(config_path=tmp_path / "nonexistent.json")
        assert cfg.is_enabled("any-skill") is True

    def test_load_and_query(self, tmp_path):
        p = tmp_path / "cfg.json"
        p.write_text('{"skills": {"a": {"enabled": false}, "b": {"enabled": true}}}')
        cfg = SkillsStateConfig(config_path=p)
        assert cfg.is_enabled("a") is False
        assert cfg.is_enabled("b") is True
        assert cfg.is_enabled("unknown") is True

    def test_set_enabled_persists(self, tmp_path):
        p = tmp_path / "cfg.json"
        cfg = SkillsStateConfig(config_path=p)
        cfg.set_enabled("x", False)
        assert cfg.is_enabled("x") is False
        # 重新加载验证持久化
        cfg2 = SkillsStateConfig(config_path=p)
        assert cfg2.is_enabled("x") is False

    def test_invalid_json_defaults(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        cfg = SkillsStateConfig(config_path=p)
        assert cfg.is_enabled("any") is True

    def test_reload(self, tmp_path):
        p = tmp_path / "cfg.json"
        p.write_text('{"skills": {"a": {"enabled": true}}}')
        cfg = SkillsStateConfig(config_path=p)
        assert cfg.is_enabled("a") is True
        p.write_text('{"skills": {"a": {"enabled": false}}}')
        cfg.reload()
        assert cfg.is_enabled("a") is False

    def test_get_all(self, tmp_path):
        p = tmp_path / "cfg.json"
        p.write_text('{"skills": {"a": {"enabled": true}, "b": {"enabled": false}}}')
        cfg = SkillsStateConfig(config_path=p)
        all_cfg = cfg.get_all()
        assert "a" in all_cfg
        assert "b" in all_cfg


# ============================================================
# 3. UnifiedSkillLoader
# ============================================================

class TestUnifiedSkillLoader:
    def test_load_declarative_skills(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        skills = loader.load(enabled_only=False)
        declarative = [s for s in skills if s.source == SkillSource.DECLARATIVE]
        names = {s.name for s in declarative}
        assert "tech-tutorial" in names
        assert "deep-research" in names
        assert "my-custom" in names

    def test_load_programmatic_skills(self, skills_root):
        @SkillRegistry.register(
            name="test-pp", description="Test post-process",
            input_type="md", output_type="json", post_process=True,
        )
        def test_pp(data):
            return data

        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        skills = loader.load(enabled_only=False)
        programmatic = [s for s in skills if s.source == SkillSource.PROGRAMMATIC]
        assert any(s.name == "test-pp" for s in programmatic)

    def test_config_disables_skill(self, skills_root, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text('{"skills": {"deep-research": {"enabled": false}}}')
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=cfg_path)
        skills = loader.load(enabled_only=True)
        assert not any(s.name == "deep-research" for s in skills)

    def test_missing_config_defaults_enabled(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        skills = loader.load(enabled_only=False)
        assert all(s.enabled for s in skills)

    def test_sorted_by_name(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        skills = loader.load(enabled_only=False)
        names = [s.name for s in skills]
        assert names == sorted(names)

    def test_get_skill(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        loader.load(enabled_only=False)
        s = loader.get_skill("tech-tutorial")
        assert s is not None
        assert s.name == "tech-tutorial"
        assert loader.get_skill("nonexistent") is None

    def test_set_enabled(self, skills_root, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=cfg_path)
        loader.load(enabled_only=False)
        assert loader.set_enabled("tech-tutorial", False) is True
        assert loader.get_skill("tech-tutorial").enabled is False
        assert loader.set_enabled("nonexistent", True) is False

    def test_categories_correct(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        loader.load(enabled_only=False)
        s_map = {s.name: s for s in loader.list_skills()}
        assert s_map["tech-tutorial"].category == SkillCategory.PUBLIC
        assert s_map["my-custom"].category == SkillCategory.CUSTOM

    def test_dedup_declarative_over_programmatic(self, skills_root):
        """声明式技能优先于同名装饰器技能"""
        @SkillRegistry.register(
            name="deep-research", description="Dup",
            input_type="md", output_type="json",
        )
        def dup(data):
            return data

        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        skills = loader.load(enabled_only=False)
        matches = [s for s in skills if s.name == "deep-research"]
        assert len(matches) == 1
        assert matches[0].source == SkillSource.DECLARATIVE


# ============================================================
# 4. ZIP 安装
# ============================================================

class TestZipInstall:
    def _make_skill_zip(self, tmp_path, name="new-skill", desc="A new skill"):
        skill_dir = tmp_path / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n",
            encoding="utf-8",
        )
        zip_path = tmp_path / f"{name}.skill"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(skill_dir / "SKILL.md", f"{name}/SKILL.md")
        return zip_path

    def test_install_valid(self, skills_root, tmp_path):
        zip_path = self._make_skill_zip(tmp_path)
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(zip_path)
        assert result["success"] is True
        assert result["skill_name"] == "new-skill"
        assert (skills_root / "custom" / "new-skill" / "SKILL.md").exists()

    def test_install_duplicate_rejected(self, skills_root, tmp_path):
        """已存在的技能不能重复安装"""
        zip_path = self._make_skill_zip(tmp_path, name="my-custom")
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(zip_path)
        assert result["success"] is False
        assert "已存在" in result["message"]

    def test_install_invalid_name(self, skills_root, tmp_path):
        zip_path = self._make_skill_zip(tmp_path, name="Invalid_Name")
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(zip_path)
        assert result["success"] is False
        assert "hyphen-case" in result["message"]

    def test_install_missing_description(self, skills_root, tmp_path):
        skill_dir = tmp_path / "no-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: no-desc\n---\n\n# X\n")
        zip_path = tmp_path / "no-desc.skill"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(skill_dir / "SKILL.md", "no-desc/SKILL.md")
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(zip_path)
        assert result["success"] is False

    def test_install_nonexistent_file(self, skills_root, tmp_path):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(tmp_path / "nope.skill")
        assert result["success"] is False

    def test_install_not_zip(self, skills_root, tmp_path):
        bad = tmp_path / "bad.skill"
        bad.write_text("not a zip")
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(bad)
        assert result["success"] is False

    def test_install_no_skill_md(self, skills_root, tmp_path):
        """ZIP 中没有 SKILL.md"""
        zip_path = tmp_path / "empty.skill"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "hello")
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(zip_path)
        assert result["success"] is False

    def test_install_desc_with_angle_brackets(self, skills_root, tmp_path):
        zip_path = self._make_skill_zip(tmp_path, name="xss-test", desc="<script>alert(1)</script>")
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        result = loader.install_from_zip(zip_path)
        assert result["success"] is False
        assert "尖括号" in result["message"]


# ============================================================
# 5. REST API
# ============================================================

class TestSkillsAPI:
    @pytest.fixture
    def app(self, skills_root, tmp_path):
        """创建 Flask 测试应用"""
        from flask import Flask
        from routes.skills_api import skills_bp, _get_loader
        import routes.skills_api as api_mod

        app = Flask(__name__)
        app.register_blueprint(skills_bp)

        # 注入测试 loader
        cfg_path = tmp_path / "cfg.json"
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=cfg_path)
        loader.load(enabled_only=False)
        api_mod._loader = loader

        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_list_skills(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "skills" in data
        names = {s["name"] for s in data["skills"]}
        assert "tech-tutorial" in names
        assert "deep-research" in names

    def test_get_skill_detail(self, client):
        resp = client.get("/api/skills/tech-tutorial")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "tech-tutorial"
        assert "content" in data
        assert "allowed_tools" in data

    def test_get_skill_not_found(self, client):
        resp = client.get("/api/skills/nonexistent")
        assert resp.status_code == 404

    def test_update_skill_enabled(self, client):
        resp = client.put(
            "/api/skills/tech-tutorial",
            json={"enabled": False},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["enabled"] is False

    def test_update_skill_missing_field(self, client):
        resp = client.put("/api/skills/tech-tutorial", json={})
        assert resp.status_code == 400

    def test_update_skill_not_found(self, client):
        resp = client.put("/api/skills/nonexistent", json={"enabled": True})
        assert resp.status_code == 404

    def test_install_no_file(self, client):
        resp = client.post("/api/skills/install")
        assert resp.status_code == 400

    def test_install_wrong_extension(self, client, tmp_path):
        import io
        data = {"file": (io.BytesIO(b"data"), "test.zip")}
        resp = client.post("/api/skills/install", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400


# ============================================================
# 6. WritingSkillManager 统一模式兼容性
# ============================================================

class TestWritingSkillManagerUnified:
    def test_unified_mode_loads_declarative_only(self, skills_root):
        @SkillRegistry.register(
            name="pp-skill", description="Post-process",
            input_type="md", output_type="json", post_process=True,
        )
        def pp(data):
            return data

        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        loader.load(enabled_only=False)
        mgr = WritingSkillManager(loader=loader)
        skills = mgr.load(enabled_only=False)
        names = [s.name for s in skills]
        assert "tech-tutorial" in names
        assert "deep-research" in names
        assert "pp-skill" not in names  # 装饰器技能不应出现

    def test_unified_mode_match_still_works(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        loader.load(enabled_only=False)
        mgr = WritingSkillManager(loader=loader)
        mgr.load(enabled_only=False)
        skill = mgr.match_skill("深度研究 AI")
        assert skill is not None
        assert skill.name == "deep-research"

    def test_unified_mode_prompt_generation(self, skills_root):
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=skills_root / "no.json")
        loader.load(enabled_only=False)
        mgr = WritingSkillManager(loader=loader)
        mgr.load(enabled_only=False)
        skill = next(s for s in mgr.list_skills() if s.name == "tech-tutorial")
        prompt = mgr.build_system_prompt_section(skill)
        assert '<writing-skill name="tech-tutorial">' in prompt

    def test_standalone_mode_still_works(self, skills_root):
        """不传 loader 时回退到独立模式"""
        mgr = WritingSkillManager(skills_root=skills_root)
        skills = mgr.load(enabled_only=False)
        names = [s.name for s in skills]
        assert "tech-tutorial" in names

    def test_unified_mode_respects_enabled(self, skills_root, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text('{"skills": {"tech-tutorial": {"enabled": false}}}')
        loader = UnifiedSkillLoader(skills_root=skills_root, config_path=cfg_path)
        loader.load(enabled_only=False)
        mgr = WritingSkillManager(loader=loader)
        skills = mgr.load(enabled_only=True)
        assert not any(s.name == "tech-tutorial" for s in skills)
