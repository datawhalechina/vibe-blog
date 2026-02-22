"""
Goal-Directed Web Extractor

Two-stage pipeline:
1. truncate_to_tokens() -- tiktoken precision truncation
2. LLM goal-directed extraction -- outputs {rational, evidence, summary}

Supports progressive degradation retry and fault-tolerant JSON parsing.
Feature toggle: GOAL_EXTRACTION_ENABLED (default false).
"""
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

GOAL_EXTRACTOR_PROMPT = """请处理以下网页内容，根据研究目标提取相关信息：

## 网页内容
{webpage_content}

## 研究目标
{goal}

## 提取指引
1. **定位依据 (rational)**: 找到网页中与研究目标直接相关的具体段落或数据
2. **原始证据 (evidence)**: 提取最相关的信息，保留原始上下文，可以超过三段
3. **精炼摘要 (summary)**: 组织为逻辑清晰的精炼段落，评估信息对研究目标的贡献度

**输出格式：JSON，包含 "rational"、"evidence"、"summary" 三个字段**
"""


@dataclass
class ExtractionResult:
    """Goal-directed extraction result."""
    rational: str = ""
    evidence: str = ""
    summary: str = ""
    success: bool = True
    error: str = ""


class GoalDirectedExtractor:
    """
    Goal-directed web content extractor.

    Pipeline:
    1. truncate_to_tokens() -- tiktoken precision truncation
    2. LLM extraction -- {rational, evidence, summary}
    3. Progressive degradation on failure
    """

    def __init__(self, llm_service=None, max_tokens: int = 95000, max_retries: int = 3):
        self.llm_service = llm_service
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self._model_name = os.environ.get("GOAL_EXTRACTOR_MODEL", "")

    def extract(self, content: str, goal: str) -> ExtractionResult:
        """Goal-directed extraction entry point."""
        if not content or not content.strip():
            return ExtractionResult(success=False, error="空内容")

        if not self.llm_service:
            truncated = self._truncate_chars(content, 2000)
            return ExtractionResult(
                rational="无 LLM 服务，返回截断原文",
                evidence=truncated,
                summary=truncated[:500],
            )

        truncated = self.truncate_to_tokens(content, self.max_tokens)
        return self._extract_with_progressive_retry(truncated, goal)

    def _extract_with_progressive_retry(self, content: str, goal: str) -> ExtractionResult:
        """Progressive degradation: shorten content on each retry."""
        current_content = content
        retry_ratios = [1.0, 0.7, 0.49, None]  # None = final fallback 25000 chars

        for i, ratio in enumerate(retry_ratios):
            if ratio is None:
                current_content = self._truncate_chars(content, 25000)
            elif ratio < 1.0:
                current_content = self._truncate_chars(content, int(len(content) * ratio))

            prompt = GOAL_EXTRACTOR_PROMPT.format(
                webpage_content=current_content, goal=goal
            )
            messages = [{"role": "user", "content": prompt}]

            try:
                kwargs = {"caller": "goal_extractor"}
                if self._model_name:
                    kwargs["model"] = self._model_name
                raw = self.llm_service.chat(messages, **kwargs)

                result = self._parse_extraction_json(raw)
                if result:
                    return ExtractionResult(
                        rational=result.get("rational", ""),
                        evidence=result.get("evidence", ""),
                        summary=result.get("summary", ""),
                    )
                logger.warning(f"Extraction empty, degrading ({i+1}/{len(retry_ratios)})")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}, degrading")

        return ExtractionResult(success=False, error="渐进式降级后仍无法提取")

    @staticmethod
    def truncate_to_tokens(text: str, max_tokens: int = 95000) -> str:
        """Tiktoken precision token truncation."""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text
            return encoding.decode(tokens[:max_tokens])
        except ImportError:
            max_chars = max_tokens * 4
            return text[:max_chars] if len(text) > max_chars else text

    @staticmethod
    def _parse_extraction_json(raw: str) -> Optional[dict]:
        """Fault-tolerant JSON parsing."""
        if not raw or not raw.strip():
            return None
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            left = text.find("{")
            right = text.rfind("}")
            if left != -1 and right != -1 and left < right:
                try:
                    return json.loads(text[left:right + 1])
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _truncate_chars(text: str, max_chars: int) -> str:
        return text[:max_chars] if len(text) > max_chars else text
