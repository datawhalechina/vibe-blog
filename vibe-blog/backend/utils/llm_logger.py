"""
LLM 调用完整日志 — 记录每次 LLM 调用的 prompt/response 到 JSONL 文件

来源：v2 方案 10
日志路径：logs/blog_tasks/{task_id}/llm_calls.jsonl

环境变量：
  LLM_CALL_LOG_ENABLED=true  (默认 true，设为 false 关闭)
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ENABLED = os.environ.get('LLM_CALL_LOG_ENABLED', 'true').lower() != 'false'


class LLMCallLogger:
    """记录每次 LLM 调用的完整输入输出到 JSONL 文件"""

    def __init__(self, task_id: str, logs_dir: str = None):
        self.task_id = task_id
        if not _ENABLED:
            self._file = None
            return

        if logs_dir:
            base = logs_dir
        elif os.environ.get("BLOG_LOGS_DIR"):
            base = os.environ["BLOG_LOGS_DIR"]
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            base = str(project_root / "logs" / "blog_tasks")

        task_dir = Path(base) / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        self._path = task_dir / "llm_calls.jsonl"
        self._file = None

    def log(
        self,
        agent: str,
        action: str,
        prompt: str,
        response: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        duration_ms: int = 0,
        model: str = "",
        **kwargs,
    ):
        """追加一条 LLM 调用记录"""
        if not _ENABLED:
            return
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agent": agent,
            "action": action,
            "model": model,
            "prompt_chars": len(prompt) if prompt else 0,
            "prompt": prompt,
            "response_chars": len(response) if response else 0,
            "response": response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
        }
        if kwargs:
            record.update(kwargs)
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"LLM 日志写入失败: {e}")

    def close(self):
        pass
