#!/usr/bin/env python3
"""
[需求点 67] TextCleanup 确定性清理管道 — 单元测试

验证 10 步正则清理管道的各步骤是否正确工作。
纯正则测试，不需要 LLM。

用法：
  cd backend
  python -m pytest tests/test_67_text_cleanup.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.text_cleanup import apply_full_cleanup


class TestStep1Fillers:
    def test_removes_chinese_fillers(self):
        text = "此外，这个方法很有效。另外，还有其他方案。"
        result = apply_full_cleanup(text)
        assert "此外，" not in result["text"]
        assert "另外，" not in result["text"]
        assert result["stats"]["fillers"] >= 2

    def test_preserves_non_filler_text(self):
        text = "这个方法很有效。它的性能很好。"
        result = apply_full_cleanup(text)
        assert "这个方法很有效" in result["text"]


class TestStep2Intensifiers:
    def test_removes_intensifiers(self):
        text = "这个框架非常强大，极其灵活，十分易用。"
        result = apply_full_cleanup(text)
        assert "非常" not in result["text"]
        assert "极其" not in result["text"]
        assert "十分" not in result["text"]
        assert result["stats"]["intensifiers"] >= 3


class TestStep4Meta:
    def test_removes_meta_comments(self):
        text = "本节将详细介绍 Docker 的核心概念。Docker 是一个容器引擎。"
        result = apply_full_cleanup(text)
        assert "本节将" not in result["text"]
        assert "Docker 是一个容器引擎" in result["text"]
        assert result["stats"]["meta"] >= 1


class TestStep5Verbose:
    def test_compresses_verbose_phrases(self):
        text = "为了能够提升性能，我们在一定程度上优化了代码。"
        result = apply_full_cleanup(text)
        assert "为了能够" not in result["text"]
        assert "在一定程度上" not in result["text"]
        assert result["stats"]["verbose"] >= 2


class TestStep6Claims:
    def test_calibrates_overconfident_claims(self):
        text = "这个方案毫无疑问地证明了其优越性。它是最好的选择。"
        result = apply_full_cleanup(text)
        assert "毫无疑问" not in result["text"]
        assert "是最好的" not in result["text"]
        assert result["stats"]["claims"] >= 2


class TestStep8TimeHallucinations:
    def test_fixes_outdated_years(self):
        import datetime
        current_year = datetime.datetime.now().year
        text = f"截至 {current_year - 1} 年，该技术已广泛应用。"
        result = apply_full_cleanup(text)
        assert f"截至{current_year}年" in result["text"]
        assert result["stats"]["time_hallucinations"] >= 1


class TestStep10Whitespace:
    def test_cleans_extra_whitespace(self):
        text = "第一段。\n\n\n\n\n第二段。  多余空格  这里。"
        result = apply_full_cleanup(text)
        assert "\n\n\n\n" not in result["text"]
        assert "  " not in result["text"]


class TestFullPipeline:
    def test_combined_cleanup(self):
        text = (
            "此外，本节将详细介绍一个非常重要的技术。"
            "这个方案毫无疑问地证明了其价值。"
            "为了能够提升效率，我们在一定程度上做了优化。"
        )
        result = apply_full_cleanup(text)
        assert result["total_fixes"] > 0
        assert "此外，" not in result["text"]
        assert "非常" not in result["text"]
        assert "毫无疑问" not in result["text"]

    def test_empty_text(self):
        result = apply_full_cleanup("")
        assert result["text"] == ""
        assert result["total_fixes"] == 0

    def test_clean_text_unchanged(self):
        text = "Docker 是一个容器引擎，用于打包和部署应用。"
        result = apply_full_cleanup(text)
        # Clean text should have minimal changes
        assert "Docker" in result["text"]
        assert "容器引擎" in result["text"]
