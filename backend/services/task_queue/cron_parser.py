"""
自然语言时间解析 → Cron 表达式 / 一次性时间

支持：
- 周期性: "每天早上8点" → cron "0 8 * * *"
- 一次性: "明天下午3点" → once + ISO datetime
"""
import re
from datetime import datetime, timedelta


def parse_schedule(text: str) -> dict:
    """
    解析自然语言时间描述

    Returns:
        {'type': 'cron', 'cron_expression': ..., 'human_readable': ...}
        {'type': 'once', 'scheduled_at': ..., 'human_readable': ...}
        {'type': 'error', 'error': ...}
    """
    text = text.strip()
    lower = text.lower()

    recurring_keywords = ['每', 'every', 'daily', 'weekly', 'monthly', '周期']
    is_recurring = any(kw in lower for kw in recurring_keywords)

    if is_recurring:
        cron = _parse_recurring(text)
        if cron:
            return {
                'type': 'cron',
                'cron_expression': cron,
                'human_readable': text,
            }

    once = _parse_once(text)
    if once:
        return {
            'type': 'once',
            'scheduled_at': once.isoformat(),
            'human_readable': text,
        }

    return {'type': 'error', 'error': f'无法解析: {text}'}


def _parse_recurring(text: str) -> str | None:
    patterns = [
        (r'每天\s*(?:早上|上午)?\s*(\d{1,2})\s*[点时](?:\s*(\d{1,2})\s*分)?',
         lambda m: f"{m.group(2) or '0'} {m.group(1)} * * *"),
        (r'每天\s*(?:下午|晚上)\s*(\d{1,2})\s*[点时](?:\s*(\d{1,2})\s*分)?',
         lambda m: (
             f"{m.group(2) or '0'} "
             f"{int(m.group(1))+12 if int(m.group(1))<12 else m.group(1)}"
             f" * * *"
         )),
        (r'每个?工作日\s*(?:早上|上午)?\s*(\d{1,2})\s*[点时]',
         lambda m: f"0 {m.group(1)} * * 1-5"),
        (r'每周([一二三四五六日天])\s*(\d{1,2})\s*[点时]',
         lambda m: f"0 {m.group(2)} * * {_weekday(m.group(1))}"),
        (r'每(\d+)\s*小时',
         lambda m: f"0 */{m.group(1)} * * *"),
        (r'每(\d+)\s*分钟',
         lambda m: f"*/{m.group(1)} * * * *"),
        (r'每月(\d+)[号日]\s*(\d{1,2})\s*[点时]',
         lambda m: f"0 {m.group(2)} {m.group(1)} * *"),
    ]
    for pattern, handler in patterns:
        match = re.search(pattern, text)
        if match:
            return handler(match)
    return None


def _parse_once(text: str) -> datetime | None:
    now = datetime.now()
    if '今天' in text:
        return _extract_time(text, now)
    if '明天' in text:
        return _extract_time(text, now + timedelta(days=1))
    if '后天' in text:
        return _extract_time(text, now + timedelta(days=2))
    return None


def _extract_time(text: str, base_date: datetime) -> datetime | None:
    match = re.search(
        r'(\d{1,2})\s*[点时](?:\s*(\d{1,2})\s*分)?', text
    )
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    if ('下午' in text or '晚上' in text) and hour < 12:
        hour += 12
    return base_date.replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


def _weekday(cn: str) -> str:
    return {
        '一': '1', '二': '2', '三': '3', '四': '4',
        '五': '5', '六': '6', '日': '0', '天': '0',
    }.get(cn, '1')
