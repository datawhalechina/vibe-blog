"""
Tests for AssemblerAgent footnote citation logic.

Uses importlib to load assembler.py directly, bypassing the heavy
services.__init__ → langgraph import chain.
"""

import re
import sys
import os
import types
import importlib.util
import pytest

_BACKEND = os.path.join(os.path.dirname(__file__), '..', '..', 'vibe-blog', 'backend')

# Stub the two direct dependencies of assembler.py so we don't pull in LLM stack.
_fake_prompts = types.ModuleType('services.blog_generator.prompts')
_fake_prompts.get_prompt_manager = lambda: None
sys.modules['services.blog_generator.prompts'] = _fake_prompts

_fake_helpers = types.ModuleType('services.blog_generator.utils.helpers')
_fake_helpers.replace_placeholders = lambda c, *a, **kw: c
_fake_helpers.estimate_reading_time = lambda *a, **kw: 5
sys.modules['services.blog_generator.utils.helpers'] = _fake_helpers

# Direct-load assembler.py via importlib to skip __init__.py chains.
_assembler_path = os.path.join(
    _BACKEND, 'services', 'blog_generator', 'agents', 'assembler.py'
)
_spec = importlib.util.spec_from_file_location(
    'services.blog_generator.agents.assembler', _assembler_path
)
_assembler_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _assembler_mod
_spec.loader.exec_module(_assembler_mod)

AssemblerAgent = _assembler_mod.AssemblerAgent


def _make_assembler():
    return AssemblerAgent()


SEARCH_RESULTS = [
    {'title': 'Redis 性能指南', 'url': 'https://example.com/redis'},
    {'title': '缓存最佳实践', 'source': 'https://example.com/cache'},
    {'title': '分布式系统', 'url': 'https://example.com/distributed'},
    {'title': '数据库优化', 'url': 'https://example.com/db'},
    {'title': '同 Redis 来源', 'url': 'https://example.com/redis/'},  # trailing slash = same as [0]
]


class TestBuildFootnoteMap:

    def test_single_reference(self):
        agent = _make_assembler()
        sections = [{'content': '效率提升了 40% {source_001}'}]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert len(fn_list) == 1
        assert fn_list[0] == (1, 'Redis 性能指南', 'https://example.com/redis')

    def test_multiple_distinct_references(self):
        agent = _make_assembler()
        sections = [
            {'content': '内容 A {source_001} 和 {source_003}'},
            {'content': '内容 B {source_002}'},
        ]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert len(fn_list) == 3
        assert fn_list[0][0] == 1  # source_001 first
        assert fn_list[1][0] == 2  # source_003 second
        assert fn_list[2][0] == 3  # source_002 third

    def test_url_deduplication_same_index(self):
        agent = _make_assembler()
        sections = [
            {'content': 'A {source_001}'},
            {'content': 'B {source_001}'},
        ]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert len(fn_list) == 1

    def test_url_deduplication_different_index_same_url(self):
        """source_001 (redis) and source_005 (redis/) normalize to the same URL."""
        agent = _make_assembler()
        sections = [{'content': '{source_001} and {source_005}'}]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert len(fn_list) == 1
        norm = agent._normalize_url('https://example.com/redis')
        assert fn_map[norm] == 1

    def test_out_of_range_index_ignored(self):
        agent = _make_assembler()
        sections = [{'content': '{source_099}'}]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert len(fn_list) == 0

    def test_empty_search_results(self):
        agent = _make_assembler()
        sections = [{'content': '{source_001}'}]
        fn_map, fn_list = agent.build_footnote_map(sections, [])
        assert fn_map == {}
        assert fn_list == []

    def test_no_placeholders(self):
        agent = _make_assembler()
        sections = [{'content': 'No references here.'}]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert fn_map == {}
        assert fn_list == []

    def test_ordering_by_first_appearance(self):
        agent = _make_assembler()
        sections = [
            {'content': '{source_003}'},  # first
            {'content': '{source_001}'},  # second
        ]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert fn_list[0][2] == 'https://example.com/distributed'  # source_003
        assert fn_list[1][2] == 'https://example.com/redis'        # source_001


class TestReplaceSourceReferences:

    def test_footnote_marker_format(self):
        agent = _make_assembler()
        sections = [{'content': '效率提升 {source_001}'}]
        fn_map, _ = agent.build_footnote_map(sections, SEARCH_RESULTS)

        result = agent.replace_source_references(
            '效率提升 {source_001}', SEARCH_RESULTS, fn_map
        )
        assert 'href="#ref-1"' in result
        assert 'data-source-url="https://example.com/redis"' in result
        assert '[1]</a></sup>' in result
        assert '{source_001}' not in result

    def test_same_source_same_number(self):
        agent = _make_assembler()
        content = '点 A {source_001} 点 B {source_001}'
        sections = [{'content': content}]
        fn_map, _ = agent.build_footnote_map(sections, SEARCH_RESULTS)
        result = agent.replace_source_references(content, SEARCH_RESULTS, fn_map)
        assert result.count('href="#ref-1"') == 2

    def test_out_of_range_preserved(self):
        agent = _make_assembler()
        content = '数据 {source_099}'
        result = agent.replace_source_references(content, SEARCH_RESULTS, {})
        assert '{source_099}' in result

    def test_legacy_mode_without_footnote_map(self):
        agent = _make_assembler()
        content = '数据 {source_001}'
        result = agent.replace_source_references(content, SEARCH_RESULTS, None)
        assert '（[Redis 性能指南](https://example.com/redis)）' in result

    def test_empty_search_results(self):
        agent = _make_assembler()
        content = '数据 {source_001}'
        result = agent.replace_source_references(content, [], {})
        assert result == content

    def test_source_with_source_key(self):
        """search_results[1] uses 'source' key instead of 'url'."""
        agent = _make_assembler()
        sections = [{'content': '{source_002}'}]
        fn_map, fn_list = agent.build_footnote_map(sections, SEARCH_RESULTS)
        assert fn_list[0][2] == 'https://example.com/cache'

        result = agent.replace_source_references('{source_002}', SEARCH_RESULTS, fn_map)
        assert 'href="#ref-1"' in result
        assert 'data-source-url="https://example.com/cache"' in result


class TestMergedReferenceLinks:
    """Verify that assemble() merges cited footnotes and uncited references
    into a single unified reference_links list."""

    def _run_assemble(self, sections, search_results, reference_links=None):
        """Helper that runs assemble() with a mock prompt manager and
        captures the kwargs passed to render_assembler_footer."""
        from unittest.mock import MagicMock

        captured = {}
        mock_pm = MagicMock()
        mock_pm.render_assembler_header.return_value = '# Title\n\n'
        def capture_footer(**kwargs):
            captured.update(kwargs)
            return '\n---\nfooter\n'
        mock_pm.render_assembler_footer.side_effect = capture_footer

        original_get_pm = _assembler_mod.get_prompt_manager
        _assembler_mod.get_prompt_manager = lambda: mock_pm

        try:
            agent = _make_assembler()
            outline = {
                'title': 'Test',
                'reference_links': reference_links or [],
                'conclusion': {'summary_points': [], 'next_steps': ''},
            }
            agent.assemble(
                outline=outline,
                sections=sections,
                code_blocks=[],
                images=[],
                search_results=search_results,
            )
        finally:
            _assembler_mod.get_prompt_manager = original_get_pm

        return captured

    def test_cited_sources_come_first(self):
        sections = [{'content': 'A {source_001} B {source_003}'}]
        uncited_links = [
            {'title': 'Extra', 'url': 'https://example.com/extra'},
        ]
        captured = self._run_assemble(sections, SEARCH_RESULTS, uncited_links)
        ref_links = captured['reference_links']

        assert len(ref_links) == 3
        assert ref_links[0]['ref_id'] == 'ref-1'
        assert ref_links[0]['url'] == 'https://example.com/redis'
        assert ref_links[1]['ref_id'] == 'ref-2'
        assert ref_links[1]['url'] == 'https://example.com/distributed'
        assert 'ref_id' not in ref_links[2]
        assert ref_links[2]['url'] == 'https://example.com/extra'

    def test_uncited_duplicate_of_cited_is_removed(self):
        sections = [{'content': '{source_001}'}]
        uncited_links = [
            {'title': 'Redis Again', 'url': 'https://example.com/redis'},
            {'title': 'New Source', 'url': 'https://example.com/new'},
        ]
        captured = self._run_assemble(sections, SEARCH_RESULTS, uncited_links)
        ref_links = captured['reference_links']

        assert len(ref_links) == 2
        assert ref_links[0]['ref_id'] == 'ref-1'
        assert ref_links[1]['url'] == 'https://example.com/new'

    def test_no_cited_footnotes_param(self):
        """cited_footnotes should no longer be passed to the footer."""
        sections = [{'content': '{source_001}'}]
        captured = self._run_assemble(sections, SEARCH_RESULTS)
        assert 'cited_footnotes' not in captured

    def test_empty_footnotes_only_uncited(self):
        sections = [{'content': 'No sources here.'}]
        uncited_links = [
            {'title': 'Some Link', 'url': 'https://example.com/some'},
        ]
        captured = self._run_assemble(sections, SEARCH_RESULTS, uncited_links)
        ref_links = captured['reference_links']
        assert len(ref_links) == 1
        assert ref_links[0]['url'] == 'https://example.com/some'


class TestNormalizeUrl:

    def test_trailing_slash(self):
        assert _make_assembler()._normalize_url('https://a.com/') == 'https://a.com'

    def test_case_insensitive(self):
        assert _make_assembler()._normalize_url('HTTPS://A.COM/Path') == 'https://a.com/path'

    def test_empty(self):
        assert _make_assembler()._normalize_url('') == ''
