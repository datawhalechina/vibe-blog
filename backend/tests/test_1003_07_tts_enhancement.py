"""
TDD 测试 — 1003.07 TTS 音频生成 / Podcast 增强
"""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.tts_service import (
    OpenAITTSProvider, VolcengineTTSProvider, TTSResult, init_tts_provider,
)
from services.podcast_service import PodcastService, NARRATE_STYLE_PROMPTS


# ── OpenAITTSProvider 测试 ──

class TestOpenAITTSProvider:
    def test_is_available_with_env(self):
        with patch.dict(os.environ, {
            "OPENAI_TTS_API_KEY": "test-key",
            "OPENAI_TTS_BASE_URL": "https://api.openai.com/v1",
        }):
            provider = OpenAITTSProvider()
            assert provider.is_available() is True

    def test_not_available_without_env(self):
        with patch.dict(os.environ, {
            "OPENAI_TTS_API_KEY": "",
            "OPENAI_TTS_BASE_URL": "",
        }, clear=False):
            provider = OpenAITTSProvider()
            assert provider.is_available() is False

    def test_voice_list_has_six(self):
        assert len(OpenAITTSProvider.VOICE_LIST) == 6
        ids = {v["id"] for v in OpenAITTSProvider.VOICE_LIST}
        assert "alloy" in ids
        assert "shimmer" in ids

    def test_truncate_short_text(self):
        provider = OpenAITTSProvider()
        text = "Hello world."
        assert provider._truncate_text(text) == text

    def test_truncate_long_text(self):
        provider = OpenAITTSProvider()
        text = "A" * 4000 + "。" + "B" * 200
        result = provider._truncate_text(text)
        assert len(result) <= 4096
        assert result.endswith("。")

    def test_truncate_no_period(self):
        provider = OpenAITTSProvider()
        text = "A" * 5000
        result = provider._truncate_text(text)
        assert len(result) <= 4096
        assert result.endswith("...")

    def test_synthesize_not_available(self):
        with patch.dict(os.environ, {"OPENAI_TTS_API_KEY": "", "OPENAI_TTS_BASE_URL": ""}):
            provider = OpenAITTSProvider()
            assert provider.synthesize("hello") is None


# ── init_tts_provider 优先级测试 ──

class TestInitTTSProvider:
    def test_prefers_openai(self):
        with patch.dict(os.environ, {
            "OPENAI_TTS_API_KEY": "key",
            "OPENAI_TTS_BASE_URL": "https://api.openai.com/v1",
            "VOLCENGINE_TTS_APPID": "app",
            "VOLCENGINE_TTS_ACCESS_TOKEN": "token",
        }):
            provider = init_tts_provider()
            assert isinstance(provider, OpenAITTSProvider)

    def test_fallback_volcengine(self):
        with patch.dict(os.environ, {
            "OPENAI_TTS_API_KEY": "",
            "OPENAI_TTS_BASE_URL": "",
            "VOLCENGINE_TTS_APPID": "app",
            "VOLCENGINE_TTS_ACCESS_TOKEN": "token",
        }):
            provider = init_tts_provider()
            assert isinstance(provider, VolcengineTTSProvider)


# ── 叙述风格 Prompt 测试 ──

class TestNarrateStylePrompts:
    def test_three_styles(self):
        assert "friendly" in NARRATE_STYLE_PROMPTS
        assert "academic" in NARRATE_STYLE_PROMPTS
        assert "concise" in NARRATE_STYLE_PROMPTS


# ── PodcastService.narrate() 测试 ──

class TestNarrate:
    def _make_service(self, llm_responses):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = llm_responses
        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm
        service.tts_provider = None
        service.output_folder = "/tmp/test_podcasts"
        os.makedirs(service.output_folder, exist_ok=True)
        return service

    def test_narrate_generates_script(self):
        service = self._make_service([
            "这是一段叙述脚本。",  # narration script
            '["关键点1", "关键点2"]',  # key points
        ])
        result = service.narrate("一篇关于 AI 的文章", style="friendly")
        assert "script" in result
        assert result["script"] == "这是一段叙述脚本。"
        assert result["has_audio"] is False
        assert result["style"] == "friendly"

    def test_narrate_skip_audio(self):
        service = self._make_service(["脚本", '["kp1"]'])
        result = service.narrate("content", skip_audio=True)
        assert result["has_audio"] is False

    def test_narrate_with_style(self):
        service = self._make_service(["学术脚本", '["kp1"]'])
        result = service.narrate("content", style="academic")
        assert result["style"] == "academic"


# ── _extract_key_points 测试 ──

class TestExtractKeyPoints:
    def test_success(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = '["Point 1", "Point 2", "Point 3"]'
        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm
        points = service._extract_key_points("Some content about AI")
        assert len(points) == 3
        assert "Point 1" in points

    def test_llm_failure(self):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception("LLM error")
        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm
        points = service._extract_key_points("content")
        assert points == []

    def test_invalid_json(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "not json"
        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm
        points = service._extract_key_points("content")
        assert points == []
