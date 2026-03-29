"""
确定性文本清理管道 — 纯正则，零 LLM 调用。
借鉴 OpenDraft text_cleanup.py，适配中文技术博客场景。

10 步管道：
  1. 删除中文填充词开头
  2. 删除空洞强化词
  3. 折叠同义词堆砌
  4. 删除 Meta 评论
  5. 压缩冗余短语
  6. 中和过度自信表述
  7. 词汇多样化（同一词 >3 次时轮换）
  8. 时间幻觉正则修复
  9. 清理 Markdown 格式问题
  10. 清理多余空白

Usage:
    from utils.text_cleanup import apply_full_cleanup
    result = apply_full_cleanup(text)
    cleaned = result["text"]
    stats = result["stats"]
"""

import re
import datetime
from typing import Dict, Any

CURRENT_YEAR = datetime.datetime.now().year

# ============================================================
# Step 1: 中文填充词开头
# ============================================================
FILLER_STARTS_ZH = [
    r"此外[，,]\s*",
    r"另外[，,]\s*",
    r"除此之外[，,]\s*",
    r"值得注意的是[，,]\s*",
    r"需要指出的是[，,]\s*",
    r"不可否认[，,]\s*",
    r"毋庸置疑[，,]\s*",
    r"众所周知[，,]\s*",
    r"总而言之[，,]\s*",
    r"综上所述[，,]\s*",
]

# ============================================================
# Step 2: 空洞强化词
# ============================================================
INTENSIFIERS_ZH = [
    (r"非常地?", ""),
    (r"极其", ""),
    (r"极为", ""),
    (r"十分地?", ""),
    (r"相当地?(?=[\u4e00-\u9fff]{2})", ""),
]

# ============================================================
# Step 3: 同义词堆砌
# ============================================================
SYNONYM_CHAINS_ZH = [
    (r"重要的[、，]关键的[、，](?:以及|和)?至关重要的", "关键的"),
    (r"全面的[、，]深入的[、，](?:以及|和)?系统的", "系统的"),
    (r"快速的?[、，]高效的?[、，](?:以及|和)?便捷的?", "高效的"),
    (r"稳定的?[、，]可靠的?[、，](?:以及|和)?健壮的?", "可靠的"),
    (r"灵活的?[、，]可扩展的?[、，](?:以及|和)?可定制的?", "灵活可扩展的"),
]

# ============================================================
# Step 4: Meta 评论
# ============================================================
META_PATTERNS_ZH = [
    r"本[节章]将(?:详细)?(?:介绍|讨论|探讨|分析|阐述)[^。]+[。]\s*",
    r"(?:接下来|下面)[，,]?(?:我们|本文)(?:将)?(?:介绍|讨论|探讨|分析)[^。]+[。]\s*",
    r"在(?:本[节章]|这[一]?部分)中[，,](?:我们|本文)(?:将)?[^。]+[。]\s*",
    r"(?:首先|其次|最后)[，,](?:我们|本文)(?:来)?(?:看看|了解|介绍)[^。]+[。]\s*",
]

# ============================================================
# Step 5: 冗余短语
# ============================================================
VERBOSE_PHRASES_ZH = [
    (r"为了能够", "为了"),
    (r"由于[^。，]{2,8}的原因", "因为"),
    (r"在[^。，]{2,8}的过程中", ""),
    (r"在一定程度上", ""),
    (r"在某种意义上", ""),
]

# ============================================================
# Step 6: 过度自信表述
# ============================================================
CLAIM_CALIBRATION_ZH = [
    (r"毫无疑问地?(?:证明|表明)了?", "有力地支持了"),
    (r"无可争辩地?", ""),
    (r"毋庸置疑地?", ""),
    (r"(?:完美|完全)(?:地)?解决了", "有效地解决了"),
    (r"是唯一的(?:方案|选择|方法)", "是一个关键的方案"),
    (r"是最(?:好|佳|优)的", "是较为有效的"),
    (r"彻底(?:改变|颠覆)了", "显著改变了"),
    (r"革命性的", "创新性的"),
]

# ============================================================
# Step 7: 词汇多样化（同一词 >3 次时轮换同义词）
# ============================================================
VOCAB_DIVERSITY_ZH = [
    ("实现", ["达成", "完成", "做到", "落地"]),
    ("提供", ["给出", "带来", "支持", "输出"]),
    ("使用", ["采用", "运用", "借助", "利用"]),
    ("通过", ["借助", "利用", "经由", "凭借"]),
    ("进行", ["开展", "执行", "实施", "推进"]),
    ("处理", ["应对", "解决", "管理", "化解"]),
    ("提升", ["改善", "优化", "增强", "强化"]),
]

# ============================================================
# Step 8: 时间幻觉正则修复
# ============================================================
TIME_HALLUCINATION_PATTERNS = [
    (rf"截至\s*{CURRENT_YEAR - 1}\s*年", f"截至{CURRENT_YEAR}年"),
    (rf"截至\s*{CURRENT_YEAR - 2}\s*年", f"截至{CURRENT_YEAR}年"),
    (rf"目前是\s*{CURRENT_YEAR - 1}\s*年", f"目前是{CURRENT_YEAR}年"),
    (rf"目前是\s*{CURRENT_YEAR - 2}\s*年", f"目前是{CURRENT_YEAR}年"),
    (rf"[Aa]s of {CURRENT_YEAR - 1}", f"as of {CURRENT_YEAR}"),
    (rf"[Aa]s of {CURRENT_YEAR - 2}", f"as of {CURRENT_YEAR}"),
    (rf"截止到?\s*{CURRENT_YEAR - 1}\s*年", f"截至{CURRENT_YEAR}年"),
    (rf"截止到?\s*{CURRENT_YEAR - 2}\s*年", f"截至{CURRENT_YEAR}年"),
]


# ============================================================
# 管道实现
# ============================================================

def _step_fillers(text: str) -> tuple:
    count = 0
    for pattern in FILLER_STARTS_ZH:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, "", text)
    return text, count


def _step_intensifiers(text: str) -> tuple:
    count = 0
    for pattern, replacement in INTENSIFIERS_ZH:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, replacement, text)
    return text, count


def _step_synonyms(text: str) -> tuple:
    count = 0
    for pattern, replacement in SYNONYM_CHAINS_ZH:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, replacement, text)
    return text, count


def _step_meta(text: str) -> tuple:
    count = 0
    for pattern in META_PATTERNS_ZH:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, "", text)
    return text, count


def _step_verbose(text: str) -> tuple:
    count = 0
    for pattern, replacement in VERBOSE_PHRASES_ZH:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, replacement, text)
    return text, count

def _step_claims(text: str) -> tuple:
    count = 0
    for pattern, replacement in CLAIM_CALIBRATION_ZH:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, replacement, text)
    return text, count


def _step_vocab_diversity(text: str) -> tuple:
    count = 0
    for word, alternatives in VOCAB_DIVERSITY_ZH:
        positions = [m.start() for m in re.finditer(re.escape(word), text)]
        if len(positions) <= 3:
            continue
        # 从第 4 次出现开始轮换（从后往前替换避免偏移）
        for i, pos in enumerate(reversed(positions[3:])):
            alt = alternatives[i % len(alternatives)]
            text = text[:pos] + alt + text[pos + len(word):]
            count += 1
    return text, count


def _step_time_hallucinations(text: str) -> tuple:
    count = 0
    for pattern, replacement in TIME_HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, text)
        count += len(matches)
        text = re.sub(pattern, replacement, text)
    return text, count


def _step_markdown(text: str) -> tuple:
    count = 0
    # 清理多余空行（>3 行 → 2 行）
    before = text
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    if text != before:
        count += 1
    # 清理行尾空格
    before = text
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    if text != before:
        count += 1
    return text, count


def _step_whitespace(text: str) -> tuple:
    count = 0
    before = text
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)
    if text != before:
        count += 1
    return text, count


def apply_full_cleanup(text: str) -> Dict[str, Any]:
    """
    10 步确定性清理管道。

    Returns:
        {"text": cleaned_text, "stats": {"fillers": N, ...}, "total_fixes": N}
    """
    stats = {}

    text, stats["fillers"] = _step_fillers(text)
    text, stats["intensifiers"] = _step_intensifiers(text)
    text, stats["synonyms"] = _step_synonyms(text)
    text, stats["meta"] = _step_meta(text)
    text, stats["verbose"] = _step_verbose(text)
    text, stats["claims"] = _step_claims(text)
    text, stats["vocab_diversified"] = _step_vocab_diversity(text)
    text, stats["time_hallucinations"] = _step_time_hallucinations(text)
    text, stats["markdown_fixes"] = _step_markdown(text)
    text, stats["whitespace"] = _step_whitespace(text)

    total = sum(stats.values())
    return {"text": text, "stats": stats, "total_fixes": total}
