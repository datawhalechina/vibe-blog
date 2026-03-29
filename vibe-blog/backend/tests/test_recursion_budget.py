"""
测试 LangGraph 递归深度预算 — _build_config() 根据 StyleProfile 动态计算 recursion_limit
"""
import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.blog_generator.style_profile import StyleProfile


def _make_generator(style: StyleProfile = None):
    """构造一个最小化的 BlogGenerator 实例（不触发真实 LLM / LangGraph）"""
    with patch('services.blog_generator.generator.TieredLLMProxy'), \
         patch('services.blog_generator.generator.MemorySaver'):
        from services.blog_generator.generator import BlogGenerator
        gen = BlogGenerator(
            llm_client=MagicMock(),
            style=style,
        )
    return gen


# ── 单元测试：_build_config 返回正确的 recursion_limit ──


class TestBuildConfigRecursionLimit:
    """各模式下 recursion_limit 应等于 base_nodes(20) + max_loops + margin(5)"""

    @pytest.mark.parametrize("mode,expected_limit", [
        ("mini", 31),
        ("short", 31),
        ("medium", 37),
        ("long", 43),
    ])
    def test_recursion_limit_by_mode(self, mode, expected_limit):
        style = getattr(StyleProfile, mode)()
        gen = _make_generator(style=style)
        state = {"topic": "test-topic", "target_length": mode}
        config = gen._build_config(state)
        assert config["recursion_limit"] == expected_limit, (
            f"mode={mode}: expected recursion_limit={expected_limit}, "
            f"got {config['recursion_limit']}"
        )

    def test_config_contains_thread_id(self):
        gen = _make_generator(style=StyleProfile.medium())
        state = {"topic": "my-topic", "target_length": "medium"}
        config = gen._build_config(state)
        assert "configurable" in config
        assert "thread_id" in config["configurable"]
        assert "my-topic" in config["configurable"]["thread_id"]


# ── 场景测试：generate / generate_stream 使用 _build_config ──


class TestGenerateUsesBuildConfig:
    """generate() 和 generate_stream() 应调用 _build_config 构建 config"""

    def test_generate_passes_recursion_limit_to_invoke(self):
        style = StyleProfile.medium()
        gen = _make_generator(style=style)
        gen.app = MagicMock()
        gen.app.invoke.return_value = {"sections": [], "final_blog": "ok"}

        gen.generate(topic="test")

        # invoke 应被调用，且 config 中包含 recursion_limit
        gen.app.invoke.assert_called_once()
        call_args = gen.app.invoke.call_args
        config_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("config")
        assert config_arg["recursion_limit"] == 37

    def test_generate_stream_passes_recursion_limit_to_stream(self):
        style = StyleProfile.medium()
        gen = _make_generator(style=style)
        gen.app = MagicMock()
        gen.app.stream.return_value = iter([])

        # generate_stream is async generator, consume it
        import asyncio
        async def _consume():
            async for _ in gen.generate_stream(topic="test"):
                pass
        asyncio.run(_consume())

        gen.app.stream.assert_called_once()
        call_args = gen.app.stream.call_args
        config_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("config")
        assert config_arg["recursion_limit"] == 37
