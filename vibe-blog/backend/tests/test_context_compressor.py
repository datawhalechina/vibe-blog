"""
上下文压缩策略 单元测试
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestFilterToolResults:
    """工具结果选择性保留测试"""

    def _make_compressor(self):
        from utils.context_compressor import ContextCompressor
        return ContextCompressor(model_name='gpt-4o')

    def test_keep_all(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'initial task'},
            {'role': 'tool', 'content': 'result 1'},
            {'role': 'tool', 'content': 'result 2'},
            {'role': 'tool', 'content': 'result 3'},
        ]
        result = comp.filter_tool_results(msgs, keep_recent=-1)
        assert all(m['content'] != 'Tool result is omitted to save tokens.' for m in result)

    def test_keep_recent_2(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'initial task'},
            {'role': 'tool', 'content': 'result 1'},
            {'role': 'tool', 'content': 'result 2'},
            {'role': 'tool', 'content': 'result 3'},
            {'role': 'tool', 'content': 'result 4'},
        ]
        result = comp.filter_tool_results(msgs, keep_recent=2)
        # First user message preserved
        assert result[0]['content'] == 'initial task'
        # Old tool results replaced
        assert result[1]['content'] == 'Tool result is omitted to save tokens.'
        assert result[2]['content'] == 'Tool result is omitted to save tokens.'
        # Recent 2 preserved
        assert result[3]['content'] == 'result 3'
        assert result[4]['content'] == 'result 4'

    def test_first_user_message_always_preserved(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'initial task'},
            {'role': 'tool', 'content': 'result 1'},
        ]
        result = comp.filter_tool_results(msgs, keep_recent=0)
        assert result[0]['content'] == 'initial task'

    def test_assistant_messages_untouched(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'task'},
            {'role': 'assistant', 'content': 'thinking...'},
            {'role': 'tool', 'content': 'old result'},
            {'role': 'assistant', 'content': 'more thinking'},
            {'role': 'tool', 'content': 'new result'},
        ]
        result = comp.filter_tool_results(msgs, keep_recent=1)
        assert result[1]['content'] == 'thinking...'
        assert result[3]['content'] == 'more thinking'

    def test_keep_zero_replaces_all_tools(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'task'},
            {'role': 'tool', 'content': 'r1'},
            {'role': 'tool', 'content': 'r2'},
        ]
        result = comp.filter_tool_results(msgs, keep_recent=0)
        assert result[1]['content'] == 'Tool result is omitted to save tokens.'
        assert result[2]['content'] == 'Tool result is omitted to save tokens.'


class TestCompressSearchResults:
    """搜索结果压缩测试"""

    def _make_compressor(self):
        from utils.context_compressor import ContextCompressor
        return ContextCompressor(model_name='gpt-4o')

    def test_limit_results(self):
        comp = self._make_compressor()
        results = [{'title': f't{i}', 'url': f'http://example.com/{i}', 'snippet': 'x' * 1000} for i in range(20)]
        compressed = comp.compress_search_results(results, max_results=5)
        assert len(compressed) == 5

    def test_truncate_snippet(self):
        comp = self._make_compressor()
        results = [{'title': 'T', 'url': 'http://a.com', 'snippet': 'x' * 1000}]
        compressed = comp.compress_search_results(results, max_chars_per_result=100)
        assert len(compressed[0]['snippet']) <= 100

    def test_dedupe_urls(self):
        comp = self._make_compressor()
        results = [
            {'title': 'A', 'url': 'http://a.com', 'snippet': 'a'},
            {'title': 'B', 'url': 'http://a.com', 'snippet': 'b'},  # duplicate
            {'title': 'C', 'url': 'http://c.com', 'snippet': 'c'},
        ]
        compressed = comp.compress_search_results(results)
        assert len(compressed) == 2


class TestCompressRevisionHistory:
    """修订历史压缩测试"""

    def _make_compressor(self):
        from utils.context_compressor import ContextCompressor
        return ContextCompressor(model_name='gpt-4o')

    def test_keep_all_when_short(self):
        comp = self._make_compressor()
        history = [{'round': 1, 'issues': ['a'], 'summary': 's1'}]
        result = comp.compress_revision_history(history, keep_last_n=2)
        assert len(result) == 1
        assert result[0].get('issues') == ['a']

    def test_compress_old_rounds(self):
        comp = self._make_compressor()
        history = [
            {'round': 1, 'issues': ['a', 'b'], 'summary': 's1', 'score': 6},
            {'round': 2, 'issues': ['c'], 'summary': 's2', 'score': 7},
            {'round': 3, 'issues': ['d'], 'summary': 's3', 'score': 8},
        ]
        result = comp.compress_revision_history(history, keep_last_n=1)
        # First 2 rounds compressed (no 'issues' key, only 'issues_count')
        assert result[0].get('issues_count') == 2
        assert 'issues' not in result[0]
        assert result[1].get('issues_count') == 1
        # Last round preserved fully
        assert result[2].get('issues') == ['d']


class TestApplyStrategy:
    """多级降级策略测试"""

    def _make_compressor(self):
        from utils.context_compressor import ContextCompressor
        return ContextCompressor(model_name='gpt-4o')

    def test_no_compression_below_70(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'task'},
            {'role': 'tool', 'content': 'result'},
        ]
        result = comp.apply_strategy(msgs, usage_ratio=0.5)
        assert result[1]['content'] == 'result'

    def test_filter_tools_at_70_85(self):
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'task'},
            {'role': 'tool', 'content': 'old1'},
            {'role': 'tool', 'content': 'old2'},
            {'role': 'tool', 'content': 'old3'},
            {'role': 'tool', 'content': 'recent1'},
            {'role': 'tool', 'content': 'recent2'},
        ]
        result = comp.apply_strategy(msgs, usage_ratio=0.75)
        # Old tools should be replaced
        assert result[1]['content'] == 'Tool result is omitted to save tokens.'

    def test_high_usage_returns_messages(self):
        """85-95% 区间也应返回消息列表"""
        comp = self._make_compressor()
        msgs = [
            {'role': 'user', 'content': 'task'},
            {'role': 'tool', 'content': 'result'},
        ]
        result = comp.apply_strategy(msgs, usage_ratio=0.90)
        assert isinstance(result, list)
        assert len(result) > 0


class TestCompressForWriter:
    """Writer 场景压缩测试"""

    def _make_compressor(self):
        from utils.context_compressor import ContextCompressor
        return ContextCompressor(model_name='gpt-4o')

    def test_basic_compress(self):
        comp = self._make_compressor()
        state = {
            'outline': {
                'topic': 'AI',
                'sections': [
                    {'title': 'Intro', 'core_question': 'What?', 'content': 'Hello' * 100},
                    {'title': 'Body', 'core_question': 'How?', 'keywords': ['ai']},
                    {'title': 'End', 'core_question': 'Why?'},
                ],
            },
            'search_results': [
                {'title': 'AI paper', 'snippet': 'about ai', 'url': 'http://a.com'},
            ],
        }
        result = comp.compress_for_writer(state, section_index=1)
        assert 'outline_summary' in result
        assert 'current_section' in result
        assert result['current_section']['title'] == 'Body'
