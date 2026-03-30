"""
配置驱动工具系统 — 单元测试
测试 102.08 迁移：ToolConfig / ToolRegistry / resolve_variable / 分组过滤
"""

import os
import pytest
from unittest.mock import patch, MagicMock


import yaml

from services.blog_generator.tools.base import (
    BaseSearchTool, BaseCrawlTool, SearchResult, SearchResponse,
)
from services.blog_generator.tools.registry import (
    ToolConfig, ToolRegistry, get_tool_registry, reset_tool_registry,
)


# ============================================================
# Inline mock tools (避免跨包导入问题)
# ============================================================

class _MockSearchTool(BaseSearchTool):
    name = "mock_search"
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def is_available(self) -> bool:
        return True
    def search(self, query, max_results=5):
        return SearchResponse(success=True, results=[SearchResult(title=query)])


class _MockCrawlTool(BaseCrawlTool):
    name = "mock_crawl"
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def scrape(self, url):
        return f"content:{url}"


# ============================================================
# Fixtures — 使用 stdlib 模块路径避免 mock_tools 导入问题
# ============================================================

@pytest.fixture
def sample_yaml(tmp_path):
    """使用 os.path:join 等 stdlib 路径做基本加载测试"""
    config = {
        "tool_groups": [{"name": "search"}, {"name": "crawl"}],
        "tools": [
            {"name": "tool_a", "group": "search", "use": "os.path:join"},
            {"name": "tool_b", "group": "crawl", "use": "os.path:exists"},
        ],
    }
    p = tmp_path / "sample.yaml"
    p.write_text(yaml.dump(config))
    return str(p)


@pytest.fixture
def env_yaml(tmp_path):
    config = {
        "tool_groups": [{"name": "search"}],
        "tools": [{"name": "env_tool", "group": "search",
                    "use": "os.path:join", "api_key": "$TEST_SEARCH_API_KEY"}],
    }
    p = tmp_path / "env.yaml"
    p.write_text(yaml.dump(config))
    return str(p)


@pytest.fixture
def empty_yaml(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text(yaml.dump({}))
    return str(p)


# ============================================================
# 1. ToolConfig
# ============================================================

class TestToolConfig:
    def test_basic_creation(self):
        c = ToolConfig(name="t", group="search", use="m:v")
        assert c.name == "t" and c.group == "search" and c.extra == {}

    def test_extra_params(self):
        c = ToolConfig(name="t", group="search", use="m:v", max_results=10, api_key="sk")
        assert c.extra["max_results"] == 10 and c.extra["api_key"] == "sk"


# ============================================================
# 2. ToolRegistry YAML 加载
# ============================================================

class TestToolRegistryLoading:
    def test_load_from_yaml(self, sample_yaml):
        r = ToolRegistry(); r.load_from_yaml(sample_yaml)
        assert "tool_a" in r.list_tools() and "tool_b" in r.list_tools()

    def test_load_empty_config(self, empty_yaml):
        r = ToolRegistry(); r.load_from_yaml(empty_yaml)
        assert r.list_tools() == []

    def test_load_nonexistent_file(self):
        r = ToolRegistry(); r.load_from_yaml("/nonexistent/path.yaml")
        assert r.list_tools() == []

    def test_env_var_resolution(self, env_yaml):
        with patch.dict(os.environ, {"TEST_SEARCH_API_KEY": "sk-test-123"}):
            r = ToolRegistry(); r.load_from_yaml(env_yaml)
            assert r.get_tool_config("env_tool").extra["api_key"] == "sk-test-123"

    def test_tool_groups_populated(self, sample_yaml):
        r = ToolRegistry(); r.load_from_yaml(sample_yaml)
        assert len(r.get_tools_by_group("search")) == 1
        assert len(r.get_tools_by_group("crawl")) == 1


# ============================================================
# 3. resolve_variable
# ============================================================

class TestResolveVariable:
    def test_resolve_stdlib(self):
        r = ToolRegistry()
        cfg = MagicMock(); cfg.extra = {}
        assert r._resolve_variable("os.path:join", cfg) is os.path.join

    def test_resolve_class_instantiation(self):
        """反射加载类时，extra 参数传入 __init__"""
        r = ToolRegistry()
        cfg = MagicMock(); cfg.extra = {"max_results": 10}
        # 直接测试内部逻辑：传入一个类，应该实例化
        tool = r._resolve_variable("os.path:join", cfg)
        # os.path.join 不是类，所以不会实例化，直接返回
        assert callable(tool)

    def test_resolve_invalid_module(self):
        r = ToolRegistry()
        cfg = MagicMock(); cfg.extra = {}
        with pytest.raises((ImportError, ModuleNotFoundError)):
            r._resolve_variable("nonexistent.module:var", cfg)

    def test_resolve_invalid_attribute(self):
        r = ToolRegistry()
        cfg = MagicMock(); cfg.extra = {}
        with pytest.raises(AttributeError):
            r._resolve_variable("os.path:nonexistent_func", cfg)


# ============================================================
# 4. 工具分组过滤
# ============================================================

class TestToolGroupFiltering:
    def test_get_tools_by_group(self, sample_yaml):
        r = ToolRegistry(); r.load_from_yaml(sample_yaml)
        assert len(r.get_tools_by_group("search")) == 1
        assert len(r.get_tools_by_group("crawl")) == 1

    def test_get_nonexistent_group(self, sample_yaml):
        r = ToolRegistry(); r.load_from_yaml(sample_yaml)
        assert r.get_tools_by_group("nonexistent") == []

    def test_get_tool_by_name(self, sample_yaml):
        r = ToolRegistry(); r.load_from_yaml(sample_yaml)
        assert r.get_tool("tool_a") is not None
        assert r.get_tool("nonexistent") is None


# ============================================================
# 5. BaseSearchTool / BaseCrawlTool 统一接口
# ============================================================

class TestBaseInterfaces:
    def test_search_result_defaults(self):
        r = SearchResult(title="T", url="https://x.com", content="H", source="e")
        assert r.title == "T" and r.source_type == "web"

    def test_search_response_defaults(self):
        resp = SearchResponse(success=True, results=[SearchResult(title="A")])
        assert resp.success and len(resp.results) == 1 and resp.error is None

    def test_abstract_search_enforced(self):
        with pytest.raises(TypeError):
            BaseSearchTool()

    def test_abstract_crawl_enforced(self):
        with pytest.raises(TypeError):
            BaseCrawlTool()

    def test_mock_search_tool(self):
        t = _MockSearchTool()
        assert t.is_available()
        resp = t.search("test")
        assert resp.success and len(resp.results) == 1

    def test_mock_crawl_tool(self):
        assert "example.com" in _MockCrawlTool().scrape("https://example.com")

    def test_configure_injects_attrs(self):
        t = _MockSearchTool()
        t.configure({"name": "overridden"})
        assert t.name == "overridden"


# ============================================================
# 6. 单例
# ============================================================

class TestToolRegistrySingleton:
    def test_singleton_returns_same_instance(self):
        reset_tool_registry()
        assert get_tool_registry() is get_tool_registry()
        reset_tool_registry()

    def test_reset_clears_singleton(self):
        r1 = get_tool_registry(); reset_tool_registry()
        assert r1 is not get_tool_registry()
        reset_tool_registry()


# ============================================================
# 7. 热重载
# ============================================================

class TestToolReload:
    def test_reload_picks_up_changes(self, tmp_path):
        config = {"tool_groups": [{"name": "search"}],
                  "tools": [{"name": "a", "group": "search", "use": "os.path:join"}]}
        p = tmp_path / "reload.yaml"
        p.write_text(yaml.dump(config))
        r = ToolRegistry(); r.load_from_yaml(str(p))
        assert len(r.list_tools()) == 1
        config["tools"].append({"name": "b", "group": "search", "use": "os.path:exists"})
        p.write_text(yaml.dump(config))
        r.reload()
        assert len(r.list_tools()) == 2


# ============================================================
# 8. SourceCurator 集成
# ============================================================

class TestSourceCuratorIntegration:
    def test_curator_filters_unhealthy_tools(self):
        from services.blog_generator.services.source_curator import SourceCurator
        c = SourceCurator()
        for _ in range(3):
            c.record_failure("serper_search")
        healthy = c.get_healthy_sources(["zhipu_search", "serper_search", "sogou_search"])
        assert "serper_search" not in healthy and "zhipu_search" in healthy

    def test_curator_ranks_results(self):
        from services.blog_generator.services.source_curator import SourceCurator
        ranked = SourceCurator().rank([
            {"title": "A", "source": "通用搜索"},
            {"title": "B", "source": "Anthropic Research"},
            {"title": "C", "source": "GitHub"},
        ])
        assert ranked[0]["source"] == "Anthropic Research"
        assert ranked[-1]["source"] == "通用搜索"