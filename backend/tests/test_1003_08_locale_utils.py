"""
TDD 测试 — 1003.08 多语言 i18n 框架（后端 locale_utils）
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.locale_utils import normalize_locale, DEFAULT_LOCALE


class TestNormalizeLocale:
    def test_none_returns_default(self):
        assert normalize_locale(None) == "zh-CN"

    def test_empty_string_returns_default(self):
        assert normalize_locale("") == "zh-CN"

    def test_zh_variants(self):
        for alias in ["zh", "zh-CN", "zh_CN", "chinese", "cn", "Chinese"]:
            assert normalize_locale(alias) == "zh-CN", f"Failed for {alias}"

    def test_en_variants(self):
        for alias in ["en", "en-US", "en_US", "english", "English"]:
            assert normalize_locale(alias) == "en-US", f"Failed for {alias}"

    def test_unknown_returns_default(self):
        assert normalize_locale("ja") == "zh-CN"
        assert normalize_locale("fr-FR") == "zh-CN"

    def test_non_string_returns_default(self):
        assert normalize_locale(123) == "zh-CN"
        assert normalize_locale(True) == "zh-CN"

    def test_whitespace_handling(self):
        assert normalize_locale("  en  ") == "en-US"
        assert normalize_locale(" zh-CN ") == "zh-CN"

    def test_case_insensitive(self):
        assert normalize_locale("EN") == "en-US"
        assert normalize_locale("ZH-CN") == "zh-CN"
        assert normalize_locale("ENGLISH") == "en-US"


class TestDefaultLocale:
    def test_default_is_zh_cn(self):
        assert DEFAULT_LOCALE == "zh-CN"
