"""
测试 PromptManager 多语言 locale-aware 加载逻辑

覆盖:
- locale 参数可选（Review C-03）
- locale 格式标准化 (zh-CN → zh_CN, en-US → en_US)
- fallback: locale 模板不存在时回退默认模板
- 英文模板加载
- 未知 locale 回退
- 便捷方法透传 locale
"""

import os
import sys
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from infrastructure.prompts.prompt_manager import PromptManager


@pytest.fixture
def locale_pm(tmp_path):
    """创建带多语言模板的 PromptManager 实例"""
    # 创建 blog 子目录
    blog_dir = tmp_path / "blog"
    blog_dir.mkdir()

    # 默认中文模板
    (blog_dir / "researcher.j2").write_text(
        "你是技术资料收集专家。主题：{{ topic }}", encoding="utf-8"
    )
    # 英文模板
    (blog_dir / "researcher.en_US.j2").write_text(
        "You are a research expert. Topic: {{ topic }}", encoding="utf-8"
    )
    # 只有中文版本的模板（测试 fallback）
    (blog_dir / "planner.j2").write_text(
        "你是大纲规划师。主题：{{ topic }}", encoding="utf-8"
    )

    return PromptManager(base_dir=str(tmp_path))


class TestLocaleParameterOptional:
    """Review C-03: locale 参数必须可选"""

    def test_render_without_locale(self, locale_pm):
        """不传 locale 时应正常工作，加载默认中文模板"""
        result = locale_pm.render("blog/researcher", topic="AI")
        assert "技术资料" in result
        assert "AI" in result

    def test_render_with_locale_none(self, locale_pm):
        """locale=None 应等同于不传"""
        result = locale_pm.render("blog/researcher", locale=None, topic="AI")
        assert "技术资料" in result

    def test_render_with_empty_string_locale(self, locale_pm):
        """locale='' 应回退到默认"""
        result = locale_pm.render("blog/researcher", locale="", topic="AI")
        assert "技术资料" in result


class TestLocaleNormalization:
    """locale 格式标准化"""

    def test_zh_cn_hyphen(self, locale_pm):
        """zh-CN 应标准化为 zh_CN，加载默认中文模板"""
        result = locale_pm.render("blog/researcher", locale="zh-CN", topic="AI")
        assert "技术资料" in result

    def test_en_us_hyphen(self, locale_pm):
        """en-US 应标准化为 en_US，加载英文模板"""
        result = locale_pm.render("blog/researcher", locale="en-US", topic="AI")
        assert "research expert" in result.lower()

    def test_en_us_underscore(self, locale_pm):
        """en_US 下划线格式也应正常工作"""
        result = locale_pm.render("blog/researcher", locale="en_US", topic="AI")
        assert "research expert" in result.lower()

    def test_en_us_formats_produce_same_result(self, locale_pm):
        """en-US 和 en_US 应产生相同结果"""
        r1 = locale_pm.render("blog/researcher", locale="en-US", topic="AI")
        r2 = locale_pm.render("blog/researcher", locale="en_US", topic="AI")
        assert r1 == r2

    def test_short_locale_en(self, locale_pm):
        """短格式 'en' 应映射到 en_US"""
        result = locale_pm.render("blog/researcher", locale="en", topic="AI")
        assert "research expert" in result.lower()

    def test_short_locale_zh(self, locale_pm):
        """短格式 'zh' 应映射到 zh_CN（默认中文）"""
        result = locale_pm.render("blog/researcher", locale="zh", topic="AI")
        assert "技术资料" in result


class TestLocaleFallback:
    """locale 模板不存在时的 fallback 行为"""

    def test_unknown_locale_falls_back_to_default(self, locale_pm):
        """未知 locale (ja-JP) 应回退到默认中文模板"""
        result = locale_pm.render("blog/researcher", locale="ja-JP", topic="AI")
        assert "技术资料" in result

    def test_no_english_template_falls_back(self, locale_pm):
        """planner 无英文模板时，en-US 应回退到中文默认"""
        result = locale_pm.render("blog/planner", locale="en-US", topic="AI")
        assert "大纲规划师" in result

    def test_default_locale_loads_base_template(self, locale_pm):
        """默认 locale (zh_CN) 应直接加载 .j2 基础模板"""
        result = locale_pm.render("blog/researcher", locale="zh-CN", topic="AI")
        assert "技术资料" in result


class TestEnglishTemplateLoading:
    """英文模板加载"""

    def test_en_us_loads_english_content(self, locale_pm):
        """en-US 应加载 .en_US.j2 英文模板"""
        result = locale_pm.render("blog/researcher", locale="en-US", topic="AI")
        assert "You are a research expert" in result
        assert "AI" in result

    def test_english_template_receives_kwargs(self, locale_pm):
        """英文模板应正确接收模板变量"""
        result = locale_pm.render("blog/researcher", locale="en-US", topic="RAG Pipeline")
        assert "RAG Pipeline" in result


class TestAutoInjectedVariables:
    """自动注入变量在多语言模板中的行为"""

    @pytest.fixture
    def pm_with_time_template(self, tmp_path):
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "timed.j2").write_text(
            "时间：{{ current_time }} 年份：{{ current_year }}", encoding="utf-8"
        )
        (blog_dir / "timed.en_US.j2").write_text(
            "Time: {{ current_time }} Year: {{ current_year }}", encoding="utf-8"
        )
        return PromptManager(base_dir=str(tmp_path))

    def test_auto_vars_injected_in_default(self, pm_with_time_template):
        result = pm_with_time_template.render("blog/timed")
        assert "年份" in result
        assert str(__import__("datetime").datetime.now().year) in result

    def test_auto_vars_injected_in_english(self, pm_with_time_template):
        result = pm_with_time_template.render("blog/timed", locale="en-US")
        assert "Year:" in result
        assert str(__import__("datetime").datetime.now().year) in result


class TestLocaleMapConstant:
    """LOCALE_MAP 常量验证"""

    def test_locale_map_exists(self):
        from infrastructure.prompts.prompt_manager import LOCALE_MAP
        assert isinstance(LOCALE_MAP, dict)

    def test_locale_map_has_common_entries(self):
        from infrastructure.prompts.prompt_manager import LOCALE_MAP
        assert "zh-CN" in LOCALE_MAP
        assert "en-US" in LOCALE_MAP
        assert "en" in LOCALE_MAP
        assert "zh" in LOCALE_MAP

    def test_default_locale_exists(self):
        from infrastructure.prompts.prompt_manager import DEFAULT_LOCALE
        assert DEFAULT_LOCALE == "zh_CN"
