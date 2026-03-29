"""
37.14 Skill 与 Agent 混合能力集成 — 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch

from services.blog_generator.skills.registry import (
    SkillRegistry, SkillDefinition,
)
from services.blog_generator.skills.executor import SkillExecutor


# ==================== SkillRegistry ====================

class TestSkillRegistry:

    def setup_method(self):
        SkillRegistry._skills.clear()

    def test_register_decorator(self):
        @SkillRegistry.register(
            name="test_skill",
            description="A test skill",
            input_type="markdown",
            output_type="json",
        )
        def my_skill(data):
            return {"result": data}

        assert "test_skill" in SkillRegistry._skills
        defn = SkillRegistry._skills["test_skill"]
        assert defn.name == "test_skill"
        assert defn.input_type == "markdown"
        assert defn.func is my_skill

    def test_get_all_skills(self):
        @SkillRegistry.register(name="a", description="A", input_type="md", output_type="json")
        def skill_a(d): return d

        @SkillRegistry.register(name="b", description="B", input_type="md", output_type="md")
        def skill_b(d): return d

        all_skills = SkillRegistry.get_all_skills()
        assert len(all_skills) == 2
        names = {s.name for s in all_skills}
        assert names == {"a", "b"}

    def test_get_post_process_skills(self):
        @SkillRegistry.register(name="pp1", description="PP1", input_type="md",
                                output_type="json", post_process=True, auto_run=True)
        def pp1(d): return d

        @SkillRegistry.register(name="pp2", description="PP2", input_type="md",
                                output_type="json", post_process=True, auto_run=False)
        def pp2(d): return d

        @SkillRegistry.register(name="normal", description="Normal", input_type="md",
                                output_type="json", post_process=False)
        def normal(d): return d

        auto_skills = SkillRegistry.get_post_process_skills(auto_only=True)
        assert len(auto_skills) == 1
        assert auto_skills[0].name == "pp1"

        all_pp = SkillRegistry.get_post_process_skills(auto_only=False)
        assert len(all_pp) == 2

    def test_get_skill_by_name(self):
        @SkillRegistry.register(name="find_me", description="X", input_type="md", output_type="json")
        def find_me(d): return d

        defn = SkillRegistry.get_skill("find_me")
        assert defn is not None
        assert defn.name == "find_me"

        assert SkillRegistry.get_skill("nonexistent") is None

    def test_register_duplicate_overwrites(self):
        @SkillRegistry.register(name="dup", description="V1", input_type="md", output_type="json")
        def v1(d): return "v1"

        @SkillRegistry.register(name="dup", description="V2", input_type="md", output_type="json")
        def v2(d): return "v2"

        assert SkillRegistry._skills["dup"].description == "V2"


# ==================== SkillExecutor ====================

class TestSkillExecutor:

    def setup_method(self):
        SkillRegistry._skills.clear()

    def test_execute_success(self):
        @SkillRegistry.register(name="echo", description="Echo", input_type="any", output_type="any")
        def echo(data):
            return {"echoed": data}

        executor = SkillExecutor(SkillRegistry)
        result = executor.execute("echo", "hello")
        assert result["success"] is True
        assert result["result"]["echoed"] == "hello"
        assert "duration_ms" in result

    def test_execute_unknown_skill(self):
        executor = SkillExecutor(SkillRegistry)
        result = executor.execute("nonexistent", "data")
        assert result["success"] is False
        assert "error" in result

    def test_execute_with_exception(self):
        @SkillRegistry.register(name="fail", description="Fail", input_type="any", output_type="any")
        def fail(data):
            raise ValueError("boom")

        executor = SkillExecutor(SkillRegistry)
        result = executor.execute("fail", "data")
        assert result["success"] is False
        assert "boom" in result["error"]

    def test_execute_batch(self):
        @SkillRegistry.register(name="s1", description="S1", input_type="any",
                                output_type="json", post_process=True)
        def s1(data):
            return {"from": "s1"}

        @SkillRegistry.register(name="s2", description="S2", input_type="any",
                                output_type="json", post_process=True)
        def s2(data):
            return {"from": "s2"}

        executor = SkillExecutor(SkillRegistry)
        results = executor.execute_batch(["s1", "s2"], {"markdown": "# Hello"})
        assert len(results) == 2
        assert results["s1"]["success"] is True
        assert results["s2"]["success"] is True

    def test_execute_batch_partial_failure(self):
        @SkillRegistry.register(name="ok", description="OK", input_type="any", output_type="json")
        def ok(data):
            return {"ok": True}

        @SkillRegistry.register(name="bad", description="Bad", input_type="any", output_type="json")
        def bad(data):
            raise RuntimeError("oops")

        executor = SkillExecutor(SkillRegistry)
        results = executor.execute_batch(["ok", "bad"], {})
        assert results["ok"]["success"] is True
        assert results["bad"]["success"] is False

    def test_execute_with_timeout(self):
        import time

        @SkillRegistry.register(name="slow", description="Slow", input_type="any",
                                output_type="any", timeout=1)
        def slow(data):
            time.sleep(5)
            return {"done": True}

        executor = SkillExecutor(SkillRegistry)
        result = executor.execute("slow", "data")
        # Should fail due to timeout
        assert result["success"] is False
