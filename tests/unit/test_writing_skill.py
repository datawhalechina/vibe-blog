"""
102.06 WritingSkillManager 单元测试
覆盖：SKILL.md 解析、技能加载、匹配、系统提示词生成、边界条件
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from services.blog_generator.skills.writing_skill_manager import (
    WritingSkill,
    WritingSkillManager,
    parse_skill_md,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def skills_root(tmp_path):
    """创建临时技能目录结构"""
    # public/tech-tutorial
    (tmp_path / "public" / "tech-tutorial").mkdir(parents=True)
    (tmp_path / "public" / "tech-tutorial" / "SKILL.md").write_text(
        "---\n"
        "name: tech-tutorial\n"
        "description: 技术教程写作技能。当用户要求写教程时使用。\n"
        "license: MIT\n"
        "allowed-tools: zhipu-search, jina-reader\n"
        "---\n\n"
        "# 技术教程写作技能\n\n"
        "## 写作方法论\n\n"
        "### Phase 1: 受众分析\n"
        "- 确定目标读者的技术水平\n",
        encoding="utf-8",
    )

    # public/deep-research
    (tmp_path / "public" / "deep-research").mkdir(parents=True)
    (tmp_path / "public" / "deep-research" / "SKILL.md").write_text(
        "---\n"
        "name: deep-research\n"
        "description: 深度研究技能。用于需要多角度调研的文章。\n"
        "license: MIT\n"
        "allowed-tools: zhipu-search, serper-google, arxiv-search\n"
        "---\n\n"
        "# 深度研究技能\n\n"
        "## 研究方法论\n",
        encoding="utf-8",
    )

    # public/problem-solution
    (tmp_path / "public" / "problem-solution").mkdir(parents=True)
    (tmp_path / "public" / "problem-solution" / "SKILL.md").write_text(
        "---\n"
        "name: problem-solution\n"
        "description: 问题解决型文章。踩坑记录、故障排查。\n"
        "license: MIT\n"
        "allowed-tools: zhipu-search\n"
        "---\n\n"
        "# 问题解决型文章\n",
        encoding="utf-8",
    )

    # custom/valid-custom
    (tmp_path / "custom" / "valid-custom").mkdir(parents=True)
    (tmp_path / "custom" / "valid-custom" / "SKILL.md").write_text(
        "---\n"
        "name: valid-custom\n"
        "description: 自定义写作风格。\n"
        "---\n\n"
        "# 自定义风格\n",
        encoding="utf-8",
    )

    # custom/no-skill-md（无 SKILL.md，应被跳过）
    (tmp_path / "custom" / "no-skill-md").mkdir(parents=True)

    # public/invalid-skill（缺少 name 字段）
    (tmp_path / "public" / "invalid-skill").mkdir(parents=True)
    (tmp_path / "public" / "invalid-skill" / "SKILL.md").write_text(
        "---\n"
        "description: 缺少 name 字段\n"
        "---\n\n"
        "# Invalid\n",
        encoding="utf-8",
    )

    return tmp_path


# ============================================================
# 1. parse_skill_md
# ============================================================

class TestParseSkillMd:
    def test_basic_parse(self, skills_root):
        skill_file = skills_root / "public" / "tech-tutorial" / "SKILL.md"
        skill = parse_skill_md(skill_file, "public")
        assert skill is not None
        assert skill.name == "tech-tutorial"
        assert "技术教程" in skill.description
        assert skill.license == "MIT"
        assert skill.category == "public"

    def test_allowed_tools_parsed(self, skills_root):
        skill_file = skills_root / "public" / "tech-tutorial" / "SKILL.md"
        skill = parse_skill_md(skill_file, "public")
        assert "zhipu-search" in skill.allowed_tools
        assert "jina-reader" in skill.allowed_tools

    def test_content_extracted(self, skills_root):
        skill_file = skills_root / "public" / "tech-tutorial" / "SKILL.md"
        skill = parse_skill_md(skill_file, "public")
        assert "# 技术教程写作技能" in skill.content
        assert "Phase 1: 受众分析" in skill.content

    def test_no_allowed_tools(self, skills_root):
        skill_file = skills_root / "custom" / "valid-custom" / "SKILL.md"
        skill = parse_skill_md(skill_file, "custom")
        assert skill is not None
        assert skill.allowed_tools == []

    def test_missing_name_returns_none(self, skills_root):
        skill_file = skills_root / "public" / "invalid-skill" / "SKILL.md"
        assert parse_skill_md(skill_file, "public") is None

    def test_nonexistent_file_returns_none(self, skills_root):
        assert parse_skill_md(skills_root / "nope" / "SKILL.md", "public") is None

    def test_wrong_filename_returns_none(self, tmp_path):
        f = tmp_path / "README.md"
        f.write_text("---\nname: x\ndescription: y\n---\n# X\n")
        assert parse_skill_md(f, "public") is None


# ============================================================
# 2. WritingSkillManager 加载
# ============================================================

class TestSkillManagerLoading:
    def test_load_all(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        skills = mgr.load(enabled_only=False)
        names = [s.name for s in skills]
        assert "tech-tutorial" in names
        assert "deep-research" in names
        assert "problem-solution" in names
        assert "valid-custom" in names
        assert "invalid-skill" not in names

    def test_sorted_by_name(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        skills = mgr.load(enabled_only=False)
        names = [s.name for s in skills]
        assert names == sorted(names)

    def test_categories_correct(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        skills = mgr.load(enabled_only=False)
        skill_map = {s.name: s for s in skills}
        assert skill_map["tech-tutorial"].category == "public"
        assert skill_map["valid-custom"].category == "custom"

    def test_empty_directory(self, tmp_path):
        empty = tmp_path / "empty_skills"
        empty.mkdir()
        mgr = WritingSkillManager(skills_root=empty)
        assert mgr.load() == []

    def test_nonexistent_directory(self, tmp_path):
        mgr = WritingSkillManager(skills_root=tmp_path / "nonexistent")
        assert mgr.load() == []


# ============================================================
# 3. 技能匹配
# ============================================================

class TestSkillMatching:
    def test_match_by_article_type(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        mgr.load(enabled_only=False)
        skill = mgr.match_skill("LangGraph 入门", article_type="tutorial")
        assert skill is not None

    def test_match_by_topic_keyword(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        mgr.load(enabled_only=False)
        skill = mgr.match_skill("深度研究 AI Agent 架构")
        assert skill is not None
        assert skill.name == "deep-research"

    def test_match_problem_keyword(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        mgr.load(enabled_only=False)
        skill = mgr.match_skill("解决 Docker 网络 problem")
        assert skill is not None
        assert skill.name == "problem-solution"

    def test_fallback_to_deep_research(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        mgr.load(enabled_only=False)
        skill = mgr.match_skill("完全无关的主题 XYZ")
        assert skill is not None
        assert skill.name == "deep-research"

    def test_auto_load_on_match(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        # 不手动 load，match_skill 应自动触发
        skill = mgr.match_skill("教程")
        assert skill is not None


# ============================================================
# 4. 系统提示词生成
# ============================================================

class TestPromptGeneration:
    def test_build_prompt_section(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        mgr.load(enabled_only=False)
        skill = next(s for s in mgr.list_skills() if s.name == "tech-tutorial")
        prompt = mgr.build_system_prompt_section(skill)
        assert '<writing-skill name="tech-tutorial">' in prompt
        assert "Phase 1: 受众分析" in prompt
        assert "</writing-skill>" in prompt

    def test_prompt_contains_methodology(self, skills_root):
        mgr = WritingSkillManager(skills_root=skills_root)
        mgr.load(enabled_only=False)
        skill = next(s for s in mgr.list_skills() if s.name == "deep-research")
        prompt = mgr.build_system_prompt_section(skill)
        assert "研究方法论" in prompt


# ============================================================
# 5. WritingSkill 数据结构
# ============================================================

class TestWritingSkillDataclass:
    def test_defaults(self):
        skill = WritingSkill(
            name="test", description="desc", license=None,
            skill_dir=None, skill_file=None, category="public",
        )
        assert skill.enabled is True
        assert skill.allowed_tools == []
        assert skill.content == ""

    def test_with_tools(self):
        skill = WritingSkill(
            name="test", description="desc", license="MIT",
            skill_dir=None, skill_file=None, category="custom",
            allowed_tools=["search", "crawl"],
        )
        assert len(skill.allowed_tools) == 2


# ============================================================
# 6. 实际 SKILL.md 文件集成测试
# ============================================================

class TestRealSkillFiles:
    """测试项目中实际的 SKILL.md 文件"""

    @pytest.fixture
    def real_skills_root(self):
        root = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'skills')
        if os.path.isdir(root):
            return root
        pytest.skip("实际 skills 目录不存在")

    def test_real_skills_loadable(self, real_skills_root):
        from pathlib import Path
        mgr = WritingSkillManager(skills_root=Path(real_skills_root))
        skills = mgr.load(enabled_only=False)
        assert len(skills) >= 3
        names = [s.name for s in skills]
        assert "tech-tutorial" in names
        assert "deep-research" in names
        assert "problem-solution" in names
