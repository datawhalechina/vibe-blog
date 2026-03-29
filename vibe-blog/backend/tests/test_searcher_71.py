"""
71 Searcher 智能搜索改造 — 单元测试

覆盖：
- 扩展搜索源（reddit_ai / hackernews + quality_weight）
- SourceCurator 排序逻辑
- 搜索源健康检查与自动降级
- AI 话题增强
"""
import time
import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ========== Task 1: 扩展搜索源 ==========

class TestExtendedSources:
    """测试新增搜索源"""

    def test_reddit_ai_in_professional_blogs(self):
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        assert 'reddit_ai' in PROFESSIONAL_BLOGS
        cfg = PROFESSIONAL_BLOGS['reddit_ai']
        assert 'reddit.com' in cfg['site']
        assert 'quality_weight' in cfg

    def test_hackernews_in_professional_blogs(self):
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        assert 'hackernews' in PROFESSIONAL_BLOGS
        cfg = PROFESSIONAL_BLOGS['hackernews']
        assert 'ycombinator' in cfg['site']
        assert 'quality_weight' in cfg

    def test_all_sources_have_quality_weight(self):
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        for src_id, cfg in PROFESSIONAL_BLOGS.items():
            assert 'quality_weight' in cfg, f"{src_id} 缺少 quality_weight"
            assert 0 < cfg['quality_weight'] <= 1.0, f"{src_id} quality_weight 超出范围"

    def test_deepmind_quality_weight(self):
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        assert PROFESSIONAL_BLOGS['deepmind']['quality_weight'] == 0.95

    def test_reddit_ai_quality_weight_lower(self):
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        assert PROFESSIONAL_BLOGS['reddit_ai']['quality_weight'] <= 0.75


# ========== Task 2: 搜索路由 ==========

class TestSearchRouting:
    """测试规则路由扩展"""

    def _make_service(self):
        from services.blog_generator.services.smart_search_service import SmartSearchService
        return SmartSearchService(llm_client=None)

    @patch('services.blog_generator.services.smart_search_service.get_search_service')
    def test_rule_routing_reddit(self, mock_ss):
        svc = self._make_service()
        result = svc._rule_based_routing("reddit 社区讨论 AI agent")
        assert 'reddit_ai' in result['sources']

    @patch('services.blog_generator.services.smart_search_service.get_search_service')
    def test_rule_routing_hackernews(self, mock_ss):
        svc = self._make_service()
        result = svc._rule_based_routing("hacker news 热门讨论")
        assert 'hackernews' in result['sources']

    @patch('services.blog_generator.services.smart_search_service.get_search_service')
    def test_rule_routing_deepmind(self, mock_ss):
        svc = self._make_service()
        result = svc._rule_based_routing("deepmind alphafold 蛋白质折叠")
        assert 'deepmind' in result['sources']


# ========== Task 3: SourceCurator ==========

class TestSourceCurator:
    """测试源质量评估"""

    def _make_curator(self):
        from services.blog_generator.services.source_curator import SourceCurator
        return SourceCurator()

    def test_rank_by_quality_weight(self):
        curator = self._make_curator()
        results = [
            {"url": "https://reddit.com/r/ai/1", "title": "Reddit Post", "source": "Reddit AI"},
            {"url": "https://deepmind.google/blog/1", "title": "DeepMind Paper", "source": "Google DeepMind"},
            {"url": "https://example.com/1", "title": "Generic", "source": "通用搜索"},
        ]
        ranked = curator.rank(results)
        # DeepMind (0.95) 应排在 Reddit (0.70) 前面
        assert ranked[0]["source"] == "Google DeepMind"

    def test_rank_empty_results(self):
        curator = self._make_curator()
        assert curator.rank([]) == []

    def test_rank_preserves_all_results(self):
        curator = self._make_curator()
        results = [
            {"url": "https://a.com", "title": "A", "source": "通用搜索"},
            {"url": "https://b.com", "title": "B", "source": "OpenAI Blog"},
        ]
        ranked = curator.rank(results)
        assert len(ranked) == 2

    def test_unknown_source_gets_default_weight(self):
        curator = self._make_curator()
        results = [
            {"url": "https://unknown.com", "title": "Unknown", "source": "未知来源"},
        ]
        ranked = curator.rank(results)
        assert len(ranked) == 1

    def test_source_weights_dict_exists(self):
        from services.blog_generator.services.source_curator import SourceCurator
        curator = SourceCurator()
        assert hasattr(curator, 'SOURCE_WEIGHTS') or hasattr(SourceCurator, 'SOURCE_WEIGHTS')


# ========== Task 4: 健康检查 ==========

class TestHealthCheck:
    """测试搜索源健康检查"""

    def _make_curator(self):
        from services.blog_generator.services.source_curator import SourceCurator
        return SourceCurator()

    def test_initial_health_all_enabled(self):
        curator = self._make_curator()
        assert curator.check_health('deepmind') is True
        assert curator.check_health('openai') is True

    def test_disable_after_3_failures(self):
        curator = self._make_curator()
        curator.record_failure('deepmind')
        curator.record_failure('deepmind')
        curator.record_failure('deepmind')
        assert curator.check_health('deepmind') is False

    def test_2_failures_still_healthy(self):
        curator = self._make_curator()
        curator.record_failure('openai')
        curator.record_failure('openai')
        assert curator.check_health('openai') is True

    def test_manual_disable_and_enable(self):
        curator = self._make_curator()
        curator.disable_source('meta_ai')
        assert curator.check_health('meta_ai') is False
        curator.enable_source('meta_ai')
        assert curator.check_health('meta_ai') is True

    def test_record_success_resets_failures(self):
        curator = self._make_curator()
        curator.record_failure('mistral')
        curator.record_failure('mistral')
        curator.record_success('mistral')
        assert curator.check_health('mistral') is True

    def test_recheck_after_cooldown(self):
        """30 分钟后自动重新检查"""
        curator = self._make_curator()
        # 模拟 3 次失败
        curator.record_failure('xai')
        curator.record_failure('xai')
        curator.record_failure('xai')
        assert curator.check_health('xai') is False

        # 模拟时间过去 31 分钟
        if hasattr(curator, '_disabled_sources') and 'xai' in curator._disabled_sources:
            curator._disabled_sources['xai'] = time.time() - 1860  # 31 min ago
        assert curator.check_health('xai') is True

    def test_get_healthy_sources(self):
        curator = self._make_curator()
        sources = ['deepmind', 'openai', 'meta_ai']
        # 禁用 openai
        curator.record_failure('openai')
        curator.record_failure('openai')
        curator.record_failure('openai')
        healthy = curator.get_healthy_sources(sources)
        assert 'deepmind' in healthy
        assert 'openai' not in healthy
        assert 'meta_ai' in healthy
