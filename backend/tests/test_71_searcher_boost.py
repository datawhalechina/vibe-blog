#!/usr/bin/env python3
"""
[需求点 71] Searcher 智能搜索改造 — Phase A + C 单元测试

验证：
  SR1  PROFESSIONAL_BLOGS 新增 5 个 AI 博客源存在且格式正确
  SR2  _is_ai_topic() 正确识别 AI 话题
  SR3  _is_ai_topic() 不误判非 AI 话题
  SR4  _boost_ai_sources() AI 话题增加正确的源
  SR5  _boost_ai_sources() 非 AI 话题不增加源
  SR11 search_router.j2 渲染包含新增源描述
  SR_SP StyleProfile.enable_ai_boost 字段存在且默认值正确

用法：
  cd backend
  python -m pytest tests/test_71_searcher_boost.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== SR1: PROFESSIONAL_BLOGS 新增源 ==========

class TestProfessionalBlogsExpansion:
    def test_new_ai_sources_exist(self):
        """SR1: 新增 5 个 AI 博客源存在"""
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS

        new_sources = ['deepmind', 'meta_ai', 'mistral', 'xai', 'ms_research']
        for src in new_sources:
            assert src in PROFESSIONAL_BLOGS, f"缺少源: {src}"

    def test_new_sources_have_required_fields(self):
        """SR1b: 新增源格式正确（site/name/keywords）"""
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS

        new_sources = ['deepmind', 'meta_ai', 'mistral', 'xai', 'ms_research']
        for src in new_sources:
            config = PROFESSIONAL_BLOGS[src]
            assert 'site' in config and config['site'], f"{src} 缺少 site"
            assert 'name' in config and config['name'], f"{src} 缺少 name"
            assert 'keywords' in config and len(config['keywords']) > 0, f"{src} 缺少 keywords"

    def test_deepmind_config(self):
        """SR1c: DeepMind 配置正确"""
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        cfg = PROFESSIONAL_BLOGS['deepmind']
        assert cfg['site'] == 'deepmind.google'
        assert 'deepmind' in cfg['keywords']

    def test_meta_ai_config(self):
        """SR1d: Meta AI 配置正确"""
        from services.blog_generator.services.smart_search_service import PROFESSIONAL_BLOGS
        cfg = PROFESSIONAL_BLOGS['meta_ai']
        assert cfg['site'] == 'ai.meta.com'
        assert 'llama' in cfg['keywords']


# ========== SR2-SR3: AI 话题检测 ==========

class TestIsAiTopic:
    def test_ai_topics_detected(self):
        """SR2: 正确识别 AI 话题"""
        from services.blog_generator.services.smart_search_service import SmartSearchService

        ai_topics = [
            "LLM Agent 架构演进",
            "Claude 3.5 Sonnet 新特性",
            "GPT-4 vs Gemini 对比",
            "RAG 检索增强生成实战",
            "大模型微调最佳实践",
            "Stable Diffusion 图像生成",
            "AI Agent 自动化工作流",
            "MCP 协议详解",
            "vibe coding 新范式",
        ]
        for topic in ai_topics:
            assert SmartSearchService._is_ai_topic(topic), f"未识别 AI 话题: {topic}"

    def test_non_ai_topics_not_detected(self):
        """SR3: 不误判非 AI 话题"""
        from services.blog_generator.services.smart_search_service import SmartSearchService

        non_ai_topics = [
            "React 性能优化指南",
            "Docker 容器化部署",
            "PostgreSQL 索引优化",
            "Kubernetes 集群管理",
            "CSS Grid 布局教程",
            "Git 分支管理策略",
        ]
        for topic in non_ai_topics:
            assert not SmartSearchService._is_ai_topic(topic), f"误判为 AI 话题: {topic}"


# ========== SR4-SR5: AI 话题增强 ==========

class TestBoostAiSources:
    def setup_method(self):
        from services.blog_generator.services.smart_search_service import SmartSearchService
        self.service = SmartSearchService()

    def test_boost_adds_ai_sources(self):
        """SR4: AI 话题增加正确的源"""
        initial = ['general']
        boosted = self.service._boost_ai_sources(initial, "Claude Agent 开发")

        # 应包含所有 AI_BOOST_SOURCES
        for src in ['anthropic', 'openai', 'google_ai', 'deepmind', 'meta_ai', 'mistral', 'huggingface']:
            assert src in boosted, f"缺少增强源: {src}"

        # 应包含 arxiv
        assert 'arxiv' in boosted

        # 原始 general 应保留
        assert 'general' in boosted

    def test_boost_no_duplicates(self):
        """SR4b: 已存在的源不重复添加"""
        initial = ['general', 'anthropic', 'openai']
        boosted = self.service._boost_ai_sources(initial, "LLM 微调")

        # anthropic 和 openai 不应重复
        assert boosted.count('anthropic') == 1
        assert boosted.count('openai') == 1

    def test_no_boost_for_non_ai(self):
        """SR5: 非 AI 话题不增加源"""
        initial = ['general', 'github']
        boosted = self.service._boost_ai_sources(initial, "React 性能优化")

        assert boosted == initial


# ========== SR11: search_router.j2 模板 ==========

class TestSearchRouterTemplate:
    def test_template_contains_new_sources(self):
        """SR11: search_router.j2 包含新增源描述"""
        from infrastructure.prompts import get_prompt_manager
        pm = get_prompt_manager()
        result = pm.render_search_router(topic="测试话题")

        new_sources = ['deepmind', 'meta_ai', 'mistral', 'xai', 'ms_research']
        for src in new_sources:
            assert src in result, f"search_router.j2 缺少源描述: {src}"


# ========== SR_SP: StyleProfile ==========

class TestStyleProfileAiBoost:
    def test_enable_ai_boost_default_true(self):
        """SR_SP: StyleProfile.enable_ai_boost 默认为 True"""
        from services.blog_generator.style_profile import StyleProfile
        sp = StyleProfile()
        assert sp.enable_ai_boost is True

    def test_mini_preset_disables_ai_boost(self):
        """SR_SP2: mini 预设关闭 AI 增强"""
        from services.blog_generator.style_profile import StyleProfile
        sp = StyleProfile.mini()
        assert sp.enable_ai_boost is False

    def test_long_preset_enables_ai_boost(self):
        """SR_SP3: long 预设开启 AI 增强"""
        from services.blog_generator.style_profile import StyleProfile
        sp = StyleProfile.long()
        assert sp.enable_ai_boost is True
