"""
Podcast 播客生成服务 — 单元测试
TDD Red Phase: 先写测试，再实现代码

覆盖:
- ScriptLine / PodcastScript 数据模型
- VolcengineTTSProvider TTS 合成
- PodcastService 管线（脚本生成、并行 TTS、音频混合、文稿生成）
- API 路由
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── 数据模型测试 ──────────────────────────────────────────────

class TestScriptLine:
    """ScriptLine 数据模型"""

    def test_create_script_line(self):
        from services.tts_service import ScriptLine
        line = ScriptLine(speaker="male", paragraph="Hello Deer")
        assert line.speaker == "male"
        assert line.paragraph == "Hello Deer"

    def test_script_line_defaults(self):
        from services.tts_service import ScriptLine
        line = ScriptLine()
        assert line.speaker == "male"
        assert line.paragraph == ""


class TestPodcastScript:
    """PodcastScript 数据模型"""

    def test_from_dict_basic(self):
        from services.tts_service import PodcastScript
        data = {
            "title": "Test Episode",
            "locale": "zh",
            "lines": [
                {"speaker": "male", "paragraph": "Hello Deer"},
                {"speaker": "female", "paragraph": "Welcome back"},
            ]
        }
        script = PodcastScript.from_dict(data)
        assert script.title == "Test Episode"
        assert script.locale == "zh"
        assert len(script.lines) == 2
        assert script.lines[0].speaker == "male"
        assert script.lines[1].paragraph == "Welcome back"

    def test_from_dict_defaults(self):
        from services.tts_service import PodcastScript
        script = PodcastScript.from_dict({})
        assert script.title == ""
        assert script.locale == "zh"
        assert script.lines == []

    def test_from_dict_invalid_lines_ignored(self):
        from services.tts_service import PodcastScript
        data = {
            "lines": [
                {"speaker": "male", "paragraph": "Valid"},
                {},  # 空行也应该能处理
            ]
        }
        script = PodcastScript.from_dict(data)
        assert len(script.lines) == 2

    def test_to_dict_roundtrip(self):
        from services.tts_service import PodcastScript
        data = {
            "title": "Roundtrip",
            "locale": "en",
            "lines": [
                {"speaker": "male", "paragraph": "Hello"},
                {"speaker": "female", "paragraph": "Hi"},
            ]
        }
        script = PodcastScript.from_dict(data)
        result = script.to_dict()
        assert result["title"] == "Roundtrip"
        assert len(result["lines"]) == 2


# ── TTS Provider 测试 ─────────────────────────────────────────

class TestVolcengineTTSProvider:
    """火山引擎 TTS Provider"""

    def test_is_available_with_env(self):
        from services.tts_service import VolcengineTTSProvider
        with patch.dict(os.environ, {
            'VOLCENGINE_TTS_APPID': 'test-app',
            'VOLCENGINE_TTS_ACCESS_TOKEN': 'test-token',
        }):
            provider = VolcengineTTSProvider()
            assert provider.is_available() is True

    def test_is_not_available_without_env(self):
        from services.tts_service import VolcengineTTSProvider
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('VOLCENGINE_TTS_APPID', None)
            os.environ.pop('VOLCENGINE_TTS_ACCESS_TOKEN', None)
            provider = VolcengineTTSProvider()
            assert provider.is_available() is False

    @patch('services.tts_service.requests.post')
    def test_synthesize_success(self, mock_post):
        """Mock HTTP 请求验证 TTS 调用参数和返回"""
        import base64
        from services.tts_service import VolcengineTTSProvider

        fake_audio = b'\xff\xfb\x90\x00' * 10
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'code': 3000,
            'data': base64.b64encode(fake_audio).decode(),
        }
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {
            'VOLCENGINE_TTS_APPID': 'app123',
            'VOLCENGINE_TTS_ACCESS_TOKEN': 'tok456',
        }):
            provider = VolcengineTTSProvider()
            result = provider.synthesize("你好世界", voice_type="male")

        assert result is not None
        assert result.audio_data == fake_audio
        # 验证请求参数
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
        assert payload['app']['appid'] == 'app123'
        assert payload['audio']['encoding'] == 'mp3'
        assert payload['audio']['speed_ratio'] == 1.2

    @patch('services.tts_service.requests.post')
    def test_synthesize_api_error(self, mock_post):
        """API 返回非 3000 code 时返回 None"""
        from services.tts_service import VolcengineTTSProvider

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'code': 4001, 'message': 'Invalid text'}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {
            'VOLCENGINE_TTS_APPID': 'app',
            'VOLCENGINE_TTS_ACCESS_TOKEN': 'tok',
        }):
            provider = VolcengineTTSProvider()
            result = provider.synthesize("test")

        assert result is None

    @patch('services.tts_service.requests.post')
    def test_synthesize_network_error(self, mock_post):
        """网络异常时返回 None"""
        from services.tts_service import VolcengineTTSProvider

        mock_post.side_effect = Exception("Connection refused")

        with patch.dict(os.environ, {
            'VOLCENGINE_TTS_APPID': 'app',
            'VOLCENGINE_TTS_ACCESS_TOKEN': 'tok',
        }):
            provider = VolcengineTTSProvider()
            result = provider.synthesize("test")

        assert result is None

    def test_voice_map_has_male_and_female(self):
        from services.tts_service import VolcengineTTSProvider
        assert "male" in VolcengineTTSProvider.VOICE_MAP
        assert "female" in VolcengineTTSProvider.VOICE_MAP


# ── PodcastService 管线测试 ───────────────────────────────────

class TestPodcastServiceTranscript:
    """Markdown 文稿生成"""

    def test_generate_transcript(self):
        from services.podcast_service import PodcastService
        from services.tts_service import PodcastScript

        script = PodcastScript.from_dict({
            "title": "AI 入门",
            "locale": "zh",
            "lines": [
                {"speaker": "male", "paragraph": "Hello Deer"},
                {"speaker": "female", "paragraph": "欢迎收听"},
            ]
        })

        service = PodcastService.__new__(PodcastService)
        md = service._generate_transcript(script)
        assert "# AI 入门" in md
        assert "**主持人 (男)**" in md or "**Host (Male)**" in md
        assert "Hello Deer" in md
        assert "欢迎收听" in md


class TestPodcastServiceMixAudio:
    """音频混合"""

    def test_mix_audio_concatenation(self):
        from services.podcast_service import PodcastService

        service = PodcastService.__new__(PodcastService)
        chunks = [b'\x01\x02', b'\x03\x04', b'\x05\x06']
        result = service._mix_audio(chunks)
        assert result == b'\x01\x02\x03\x04\x05\x06'

    def test_mix_audio_empty(self):
        from services.podcast_service import PodcastService

        service = PodcastService.__new__(PodcastService)
        result = service._mix_audio([])
        assert result == b''


class TestPodcastServiceParallelTTS:
    """并行 TTS 合成"""

    def test_parallel_tts_ordering(self):
        """并行 TTS 结果按原始顺序组装"""
        from services.podcast_service import PodcastService
        from services.tts_service import PodcastScript, TTSResult

        script = PodcastScript.from_dict({
            "lines": [
                {"speaker": "male", "paragraph": "Line 1"},
                {"speaker": "female", "paragraph": "Line 2"},
                {"speaker": "male", "paragraph": "Line 3"},
            ]
        })

        mock_provider = MagicMock()
        # 模拟每行返回不同的音频数据
        mock_provider.synthesize.side_effect = [
            TTSResult(audio_data=b'audio_1'),
            TTSResult(audio_data=b'audio_2'),
            TTSResult(audio_data=b'audio_3'),
        ]

        service = PodcastService.__new__(PodcastService)
        service.tts_provider = mock_provider

        chunks = service._parallel_tts(script)
        assert len(chunks) == 3
        assert chunks[0] == b'audio_1'
        assert chunks[1] == b'audio_2'
        assert chunks[2] == b'audio_3'

    def test_parallel_tts_skip_failed(self):
        """失败行跳过，不影响其他行"""
        from services.podcast_service import PodcastService
        from services.tts_service import PodcastScript, TTSResult

        script = PodcastScript.from_dict({
            "lines": [
                {"speaker": "male", "paragraph": "Line 1"},
                {"speaker": "female", "paragraph": "Line 2"},
                {"speaker": "male", "paragraph": "Line 3"},
            ]
        })

        mock_provider = MagicMock()
        mock_provider.synthesize.side_effect = [
            TTSResult(audio_data=b'audio_1'),
            None,  # 第二行失败
            TTSResult(audio_data=b'audio_3'),
        ]

        service = PodcastService.__new__(PodcastService)
        service.tts_provider = mock_provider

        chunks = service._parallel_tts(script)
        assert len(chunks) == 2
        assert chunks[0] == b'audio_1'
        assert chunks[1] == b'audio_3'


class TestPodcastServiceGenerateScript:
    """LLM 脚本生成"""

    def test_generate_script_parses_json(self):
        """Mock LLM 验证 JSON 解析"""
        from services.podcast_service import PodcastService

        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "title": "AI 播客",
            "locale": "zh",
            "lines": [
                {"speaker": "male", "paragraph": "Hello Deer"},
                {"speaker": "female", "paragraph": "今天聊 AI"},
            ]
        })

        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm

        script = service._generate_script("一篇关于 AI 的文章", locale="zh")
        assert script is not None
        assert len(script.lines) == 2
        assert script.lines[0].paragraph == "Hello Deer"

    def test_generate_script_handles_markdown_json(self):
        """LLM 返回 ```json 包裹的 JSON"""
        from services.podcast_service import PodcastService

        mock_llm = MagicMock()
        mock_llm.chat.return_value = '```json\n{"title":"Test","locale":"zh","lines":[{"speaker":"male","paragraph":"Hi"}]}\n```'

        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm

        script = service._generate_script("content", locale="zh")
        assert script is not None
        assert len(script.lines) == 1

    def test_generate_script_llm_failure(self):
        """LLM 返回 None 时返回 None"""
        from services.podcast_service import PodcastService

        mock_llm = MagicMock()
        mock_llm.chat.return_value = None

        service = PodcastService.__new__(PodcastService)
        service.llm_service = mock_llm

        script = service._generate_script("content")
        assert script is None


# ── API 路由测试 ──────────────────────────────────────────────

class TestPodcastRoutes:
    """播客 API 路由"""

    @pytest.fixture
    def app(self):
        """创建测试 Flask 应用"""
        from flask import Flask
        from routes.podcast_routes import podcast_bp

        app = Flask(__name__)
        app.register_blueprint(podcast_bp)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_generate_missing_content(self, client):
        """缺少 content 参数返回 400"""
        resp = client.post('/api/podcast/generate', json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    @patch('routes.podcast_routes.get_podcast_service')
    def test_generate_service_unavailable(self, mock_get_svc, client):
        """服务不可用返回 503"""
        mock_get_svc.return_value = None
        resp = client.post('/api/podcast/generate', json={'content': 'test'})
        assert resp.status_code == 503

    @patch('routes.podcast_routes.get_podcast_service')
    def test_generate_success(self, mock_get_svc, client):
        """正常生成返回 task_id"""
        mock_svc = MagicMock()
        mock_svc.is_available.return_value = True
        mock_get_svc.return_value = mock_svc

        resp = client.post('/api/podcast/generate', json={
            'content': '一篇关于 AI 的文章',
            'title': 'AI 播客',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'task_id' in data
