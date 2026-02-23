"""
Podcast 播客生成服务 — 脚本编写 + TTS 合成 + 音频混合管线

三阶段管线:
1. LLM 生成双人对话脚本 (Script JSON)
2. 并行 TTS 合成 (ThreadPoolExecutor)
3. 音频混合 + Markdown 文稿生成
"""
import json
import logging
import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List

from services.tts_service import (
    PodcastScript, ScriptLine, TTSProvider, TTSResult,
    VolcengineTTSProvider, get_tts_provider, init_tts_provider,
)

logger = logging.getLogger(__name__)

# ── Podcast 脚本生成 Prompt ───────────────────────────────────

PODCAST_SCRIPT_SYSTEM_PROMPT = """你是一位专业的播客脚本编剧。你的任务是将用户提供的文章内容转化为一段双人对话播客脚本。

## 输出格式

请输出 JSON 格式，结构如下：
```json
{
  "title": "播客标题",
  "locale": "zh",
  "lines": [
    {"speaker": "male", "paragraph": "对话内容"},
    {"speaker": "female", "paragraph": "对话内容"}
  ]
}
```

## 脚本编写规则

1. 固定两位主持人：male（男）和 female（女），交替发言
2. 第一句必须由 male 说 "Hello Deer，欢迎收听本期播客"
3. 对话风格：自然口语化、频繁互动、短句为主、避免学术腔调
4. 目标 40-60 行对话，约 10 分钟播客
5. 纯文本，不要 Markdown 格式
6. 内容要忠实于原文，但用对话方式重新组织
7. 结尾要有自然的收尾和告别"""

PODCAST_SCRIPT_USER_PROMPT = """请将以下内容转化为播客脚本：

## 标题
{title}

## 内容
{content}

请输出 JSON 格式的播客脚本："""

# ── 1003.07 叙述风格 Prompt ──────────────────────────────────

NARRATE_STYLE_PROMPTS = {
    "friendly": '你是一位友好、平易近人的导师。使用"我们"、"咱们"拉近距离，语气轻松但专业，适当加入互动引导。',
    "academic": '你是一位资深学者，正在进行学术讲座。使用严谨专业的语言，保持清晰的引言-正文-结论结构。',
    "concise": '你是一位高效的知识传播者。直接明了，先总后分，只涵盖最核心的内容。',
}


# ── PodcastService ────────────────────────────────────────────

class PodcastService:
    """播客生成服务"""

    def __init__(self, llm_service, tts_provider: Optional[TTSProvider] = None):
        self.llm_service = llm_service
        self.tts_provider = tts_provider or get_tts_provider()
        self.output_folder = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'outputs', 'podcasts'
        )
        os.makedirs(self.output_folder, exist_ok=True)

    def is_available(self) -> bool:
        """检查服务是否可用（至少需要 LLM 服务）"""
        return self.llm_service is not None and self.llm_service.is_available()

    # ── 脚本生成 ─────────────────────────────────────────────

    def _generate_script(
        self, content: str, title: str = "", locale: str = "zh"
    ) -> Optional[PodcastScript]:
        """调用 LLM 生成播客对话脚本"""
        user_prompt = PODCAST_SCRIPT_USER_PROMPT.format(
            title=title or "未命名播客",
            content=content[:8000],  # 限制输入长度
        )
        messages = [
            {"role": "system", "content": PODCAST_SCRIPT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self.llm_service.chat(
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"},
            caller="podcast_script_writer",
        )

        if not response:
            logger.error("LLM 脚本生成失败: 返回为空")
            return None

        return self._parse_script_json(response, locale)

    def _parse_script_json(self, text: str, locale: str = "zh") -> Optional[PodcastScript]:
        """解析 LLM 返回的 JSON 脚本"""
        # 提取 ```json ... ``` 包裹的内容
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        json_str = json_match.group(1) if json_match else text.strip()

        # 尝试找到 JSON 对象
        if json_str.startswith('{'):
            last_brace = json_str.rfind('}')
            if last_brace > 0:
                json_str = json_str[:last_brace + 1]

        try:
            data = json.loads(json_str)
            data.setdefault("locale", locale)
            return PodcastScript.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"脚本 JSON 解析失败: {e}")
            return None

    # ── 并行 TTS ─────────────────────────────────────────────

    def _parallel_tts(
        self, script: PodcastScript, max_workers: int = 4
    ) -> List[bytes]:
        """并行 TTS 合成，按原始顺序返回音频块"""
        if not self.tts_provider:
            logger.error("TTS Provider 不可用")
            return []

        total = len(script.lines)
        results: Dict[int, Optional[bytes]] = {}

        def _process(idx: int, line: ScriptLine) -> tuple:
            result = self.tts_provider.synthesize(line.paragraph, voice_type=line.speaker)
            return idx, result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process, i, line): i
                for i, line in enumerate(script.lines)
            }
            for future in as_completed(futures):
                try:
                    idx, tts_result = future.result()
                    results[idx] = tts_result.audio_data if tts_result else None
                except Exception as e:
                    idx = futures[future]
                    logger.warning(f"TTS 第 {idx + 1}/{total} 行失败: {e}")
                    results[idx] = None

        # 按顺序收集，跳过失败行
        audio_chunks = []
        for i in range(total):
            audio = results.get(i)
            if audio:
                audio_chunks.append(audio)

        logger.info(f"TTS 合成完成: {len(audio_chunks)}/{total} 行成功")
        return audio_chunks

    # ── 音频混合 ─────────────────────────────────────────────

    def _mix_audio(self, audio_chunks: List[bytes]) -> bytes:
        """拼接音频块为完整 MP3"""
        return b"".join(audio_chunks)

    # ── 文稿生成 ─────────────────────────────────────────────

    def _generate_transcript(self, script: PodcastScript) -> str:
        """生成 Markdown 格式文稿"""
        lines = [f"# {script.title or 'Podcast Script'}", ""]
        for line in script.lines:
            speaker = "**主持人 (男)**" if line.speaker == "male" else "**主持人 (女)**"
            lines.append(f"{speaker}: {line.paragraph}")
            lines.append("")
        return "\n".join(lines)

    # ── 1003.07 单人叙述模式 ────────────────────────────────────

    def narrate(self, content: str, style: str = "friendly",
                voice: str = None, skip_audio: bool = False) -> Dict[str, Any]:
        """单人叙述模式 — 借鉴 DeepTutor NarratorAgent"""
        script_text = self._generate_narration_script(content, style)
        key_points = self._extract_key_points(content)
        result = {
            "script": script_text,
            "key_points": key_points,
            "style": style,
            "has_audio": False,
        }
        if not skip_audio and self.tts_provider and self.tts_provider.is_available():
            tts_result = self.tts_provider.synthesize(script_text, voice_type=voice or "alloy")
            if tts_result:
                audio_filename = f"narrate_{uuid.uuid4().hex[:8]}.mp3"
                audio_path = os.path.join(self.output_folder, audio_filename)
                with open(audio_path, "wb") as f:
                    f.write(tts_result.audio_data)
                result["audio_path"] = audio_path
                result["has_audio"] = True
        return result

    def _generate_narration_script(self, content: str, style: str = "friendly") -> str:
        """生成单人叙述脚本"""
        style_prompt = NARRATE_STYLE_PROMPTS.get(style, NARRATE_STYLE_PROMPTS["friendly"])
        messages = [
            {"role": "system", "content": f"{style_prompt}\n\n请将以下内容转化为口语化的叙述稿件，适合朗读。只输出叙述文本，不要 JSON 或 Markdown 格式。"},
            {"role": "user", "content": content[:6000]},
        ]
        try:
            response = self.llm_service.chat(
                messages=messages, temperature=0.7, caller="narration_script_writer",
            )
            return (response or "").strip()
        except Exception as e:
            logger.warning(f"叙述脚本生成失败: {e}")
            return ""

    def _extract_key_points(self, content: str) -> List[str]:
        """从内容中提取 3-5 个关键点"""
        messages = [
            {"role": "system", "content": "你是一位内容分析专家。请从给定的内容中提取3-5个关键点。\n输出格式：JSON数组，每个元素是一个字符串。\n只输出JSON数组，不要包含其他内容。"},
            {"role": "user", "content": f"请从以下内容中提取关键点：\n\n{content[:4000]}"},
        ]
        try:
            response = self.llm_service.chat(
                messages=messages, temperature=0.3, caller="key_points_extractor",
            )
            if response:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"关键点提取失败: {e}")
        return []

    # ── 完整管线 ─────────────────────────────────────────────

    def generate_podcast(
        self,
        task_id: str,
        content: str,
        title: str = "",
        locale: str = "zh",
        task_manager=None,
    ) -> Dict[str, Any]:
        """
        完整播客生成管线

        Args:
            task_id: 任务 ID（用于 SSE 进度推送）
            content: 原始文章内容
            title: 播客标题
            locale: 语言 (zh/en)
            task_manager: TaskManager 实例（可选，用于 SSE）

        Returns:
            {'success': bool, 'audio_path': str, 'transcript': str, ...}
        """
        def _send_progress(stage: str, progress: int, message: str):
            if task_manager:
                task_manager.send_progress(task_id, stage, progress, message)

        try:
            # Stage 1: 生成脚本 (0-20%)
            _send_progress("script", 0, "正在生成播客脚本...")
            script = self._generate_script(content, title=title, locale=locale)
            if not script or not script.lines:
                return {"success": False, "error": "脚本生成失败"}
            _send_progress("script", 100, f"脚本生成完成: {len(script.lines)} 行对话")

            # 生成文稿
            transcript = self._generate_transcript(script)

            # Stage 2: TTS 合成 (20-80%)
            if self.tts_provider and self.tts_provider.is_available():
                _send_progress("tts", 0, "正在合成语音...")
                audio_chunks = self._parallel_tts(script)
                _send_progress("tts", 100, f"语音合成完成: {len(audio_chunks)} 段")

                if not audio_chunks:
                    return {
                        "success": True,
                        "audio_path": None,
                        "transcript": transcript,
                        "script": script.to_dict(),
                        "warning": "TTS 合成失败，仅生成文稿",
                    }

                # Stage 3: 混音 (80-100%)
                _send_progress("mix", 0, "正在混合音频...")
                audio_data = self._mix_audio(audio_chunks)

                # 保存 MP3
                audio_filename = f"podcast_{task_id}.mp3"
                audio_path = os.path.join(self.output_folder, audio_filename)
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                _send_progress("mix", 100, "播客生成完成")

                return {
                    "success": True,
                    "audio_path": audio_path,
                    "transcript": transcript,
                    "script": script.to_dict(),
                    "audio_size": len(audio_data),
                    "lines_total": len(script.lines),
                    "lines_success": len(audio_chunks),
                }
            else:
                # TTS 不可用，仅返回脚本和文稿
                return {
                    "success": True,
                    "audio_path": None,
                    "transcript": transcript,
                    "script": script.to_dict(),
                    "warning": "TTS 服务不可用，仅生成文稿",
                }

        except Exception as e:
            logger.error(f"播客生成失败: {e}", exc_info=True)
            if task_manager:
                task_manager.send_error(task_id, "podcast", str(e))
            return {"success": False, "error": str(e)}


# ── 全局服务实例 ─────────────────────────────────────────────

_podcast_service: Optional[PodcastService] = None


def get_podcast_service() -> Optional[PodcastService]:
    return _podcast_service


def init_podcast_service(llm_service, tts_provider=None) -> Optional[PodcastService]:
    global _podcast_service
    if not tts_provider:
        init_tts_provider()
        tts_provider = get_tts_provider()
    _podcast_service = PodcastService(llm_service=llm_service, tts_provider=tts_provider)
    logger.info(f"播客服务已初始化 (TTS: {'可用' if tts_provider else '不可用，仅文稿模式'})")
    return _podcast_service
