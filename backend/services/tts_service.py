"""
TTS 语音合成服务 — 抽象层 + 多引擎实现

提供 TTSProvider 抽象接口和火山引擎实现。
数据模型: ScriptLine / PodcastScript 用于播客脚本结构化表示。
"""
import abc
import base64
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional, Literal, List

import requests

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────────

@dataclass
class ScriptLine:
    """播客脚本单行"""
    speaker: str = "male"  # "male" | "female"
    paragraph: str = ""


@dataclass
class PodcastScript:
    """播客脚本"""
    title: str = ""
    locale: str = "zh"  # "zh" | "en"
    lines: List[ScriptLine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PodcastScript":
        script = cls(
            title=data.get("title", ""),
            locale=data.get("locale", "zh"),
        )
        for line in data.get("lines", []):
            script.lines.append(ScriptLine(
                speaker=line.get("speaker", "male"),
                paragraph=line.get("paragraph", ""),
            ))
        return script

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "locale": self.locale,
            "lines": [
                {"speaker": l.speaker, "paragraph": l.paragraph}
                for l in self.lines
            ],
        }


# ── TTS 结果 ─────────────────────────────────────────────────

@dataclass
class TTSResult:
    """TTS 合成结果"""
    audio_data: bytes
    duration_ms: int = 0
    voice_type: str = ""


# ── TTS Provider 抽象 ────────────────────────────────────────

class TTSProvider(abc.ABC):
    """TTS 引擎抽象基类"""

    @abc.abstractmethod
    def synthesize(self, text: str, voice_type: str = "male") -> Optional[TTSResult]:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...


# ── 火山引擎 TTS ─────────────────────────────────────────────

class VolcengineTTSProvider(TTSProvider):
    """火山引擎 TTS 实现"""

    VOICE_MAP = {
        "male": "zh_male_yangguangqingnian_moon_bigtts",
        "female": "zh_female_sajiaonvyou_moon_bigtts",
    }
    API_URL = "https://openspeech.bytedance.com/api/v1/tts"

    def __init__(self):
        self.app_id = os.getenv("VOLCENGINE_TTS_APPID", "")
        self.access_token = os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN", "")
        self.cluster = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")

    def is_available(self) -> bool:
        return bool(self.app_id and self.access_token)

    def synthesize(self, text: str, voice_type: str = "male") -> Optional[TTSResult]:
        voice = self.VOICE_MAP.get(voice_type, self.VOICE_MAP["male"])
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer;{self.access_token}",
        }
        payload = {
            "app": {"appid": self.app_id, "token": "access_token", "cluster": self.cluster},
            "user": {"uid": "vibe-blog-podcast"},
            "audio": {"voice_type": voice, "encoding": "mp3", "speed_ratio": 1.2},
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }
        try:
            resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=30)
            result = resp.json()
            if result.get("code") != 3000:
                logger.error(f"Volcengine TTS error: code={result.get('code')}, msg={result.get('message')}")
                return None
            audio = base64.b64decode(result["data"])
            return TTSResult(audio_data=audio, voice_type=voice)
        except Exception as e:
            logger.error(f"TTS synthesize failed: {e}")
            return None


# ── 全局 TTS Provider ────────────────────────────────────────

_tts_provider: Optional[TTSProvider] = None


def get_tts_provider() -> Optional[TTSProvider]:
    return _tts_provider


# ── OpenAI TTS ───────────────────────────────────────────────

class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS 实现（兼容 Azure OpenAI）— 1003.07"""

    VOICE_LIST = [
        {"id": "alloy", "name": "Alloy", "description": "Neutral and balanced"},
        {"id": "echo", "name": "Echo", "description": "Warm and conversational"},
        {"id": "fable", "name": "Fable", "description": "Expressive and dramatic"},
        {"id": "onyx", "name": "Onyx", "description": "Deep and authoritative"},
        {"id": "nova", "name": "Nova", "description": "Friendly and upbeat"},
        {"id": "shimmer", "name": "Shimmer", "description": "Clear and pleasant"},
    ]
    MAX_CHARS = 4096

    def __init__(self):
        self.model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self.api_key = os.getenv("OPENAI_TTS_API_KEY", "")
        self.base_url = os.getenv("OPENAI_TTS_BASE_URL", "")
        self.default_voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    def is_available(self) -> bool:
        return bool(self.api_key and self.base_url)

    def synthesize(self, text: str, voice_type: str = "alloy") -> Optional[TTSResult]:
        if not self.is_available():
            return None
        text = self._truncate_text(text)
        valid_voices = {v["id"] for v in self.VOICE_LIST}
        voice = voice_type if voice_type in valid_voices else self.default_voice
        try:
            resp = requests.post(
                f"{self.base_url.rstrip('/')}/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "voice": voice, "input": text},
                timeout=60,
            )
            if resp.status_code == 200:
                return TTSResult(audio_data=resp.content, voice_type=voice)
            logger.error(f"OpenAI TTS error: {resp.status_code} {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"OpenAI TTS failed: {e}")
            return None

    def _truncate_text(self, text: str) -> str:
        """智能截断到 MAX_CHARS，在最近的句号处截断"""
        if len(text) <= self.MAX_CHARS:
            return text
        truncated = text[:self.MAX_CHARS - 3]
        last_period = max(
            truncated.rfind("。"), truncated.rfind("！"), truncated.rfind("？"),
            truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"),
        )
        if last_period > self.MAX_CHARS - 500:
            return truncated[:last_period + 1]
        return truncated + "..."


def init_tts_provider() -> Optional[TTSProvider]:
    """根据环境变量初始化 TTS Provider，优先 OpenAI，回退火山引擎"""
    global _tts_provider
    # 优先尝试 OpenAI TTS
    openai_provider = OpenAITTSProvider()
    if openai_provider.is_available():
        _tts_provider = openai_provider
        logger.info("TTS 服务已初始化: OpenAI")
        return _tts_provider
    # 回退到火山引擎
    volc_provider = VolcengineTTSProvider()
    if volc_provider.is_available():
        _tts_provider = volc_provider
        logger.info("TTS 服务已初始化: Volcengine")
        return _tts_provider
    logger.warning("TTS 服务不可用: 缺少 TTS 配置")
    return None
