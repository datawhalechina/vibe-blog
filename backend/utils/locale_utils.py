"""
统一语言标准化工具 — 1003.08

参考 DeepTutor src/services/config/loader.py:173-197 的 parse_language()
"""

from typing import Any

# 语言别名映射
_LANGUAGE_ALIASES = {
    "zh": "zh-CN", "zh-cn": "zh-CN", "zh_cn": "zh-CN",
    "chinese": "zh-CN", "cn": "zh-CN",
    "en": "en-US", "en-us": "en-US", "en_us": "en-US",
    "english": "en-US",
}

DEFAULT_LOCALE = "zh-CN"


def normalize_locale(language: Any) -> str:
    """
    标准化语言代码为 BCP 47 格式。

    Args:
        language: 任意语言输入 ("zh"/"en"/"chinese"/"en-US" 等)

    Returns:
        标准化的 locale: "zh-CN" 或 "en-US"，默认 "zh-CN"
    """
    if not language:
        return DEFAULT_LOCALE
    if isinstance(language, str):
        return _LANGUAGE_ALIASES.get(language.lower().strip(), DEFAULT_LOCALE)
    return DEFAULT_LOCALE
