"""
自然语言时间解析 → Cron 表达式 / 一次性时间

两层解析策略：
1. 正则快速路径（免费、无延迟）
2. LLM fallback（覆盖任意自然语言）

支持：
- 周期性: "每天早上8点" → cron "0 8 * * *"
- 一次性: "明天下午3点" → once + ISO datetime
- 复杂表达: "工作日早上9点半写一篇AI博客" → LLM 解析
"""
import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def parse_schedule(text: str) -> dict:
    """
    解析自然语言时间描述

    Returns:
        {'type': 'cron', 'cron_expression': ..., 'human_readable': ...}
        {'type': 'once', 'scheduled_at': ..., 'human_readable': ...}
        {'type': 'error', 'error': ...}
    """
    text = text.strip()
    if not text:
        return {'type': 'error', 'error': '输入为空'}

    # 第一层：正则快速路径
    result = _parse_by_regex(text)
    if result:
        return result

    # 第二层：LLM 解析
    result = _parse_by_llm(text)
    if result:
        return result

    return {'type': 'error', 'error': f'无法解析: {text}'}


def _parse_by_regex(text: str) -> dict | None:
    """正则快速路径"""
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

    return None


def _parse_by_llm(text: str) -> dict | None:
    """
    LLM 解析自然语言 → 定时任务配置

    调用大模型，输出结构化 JSON。
    """
    try:
        from services.llm_service import get_llm_service
        llm = get_llm_service()
        if not llm or not llm.is_available():
            logger.warning("[cron_parser] LLM 服务不可用，跳过 LLM 解析")
            return None
    except ImportError:
        return None

    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    weekday_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]

    messages = [
        {
            "role": "system",
            "content": f"""你是一个时间解析助手。将用户的自然语言时间描述转换为定时任务配置。

当前时间: {now_str} ({weekday_cn})
时区: Asia/Shanghai

输出 JSON 格式（不要输出其他内容）：

周期性任务:
{{"type": "cron", "cron_expression": "分 时 日 月 周", "human_readable": "人类可读描述"}}

一次性任务:
{{"type": "once", "scheduled_at": "ISO 8601 格式", "human_readable": "人类可读描述"}}

无法解析:
{{"type": "error", "error": "原因"}}

规则:
- cron 表达式使用标准 5 段格式: 分 时 日 月 周
- 周: 0=周日, 1=周一, ..., 6=周六
- "工作日" = 1-5
- 一次性任务的时间必须在当前时间之后
- 如果用户说"下周一"，计算出具体日期
- 只输出 JSON，不要解释"""
        },
        {
            "role": "user",
            "content": text,
        },
    ]

    try:
        response = llm.chat(
            messages,
            response_format={"type": "json_object"},
            caller="cron_parser",
        )
        if not response:
            return None

        result = json.loads(response)

        # 验证返回格式
        if result.get('type') == 'cron' and result.get('cron_expression'):
            # 验证 cron 表达式有效性
            try:
                from croniter import croniter
                croniter(result['cron_expression'])
            except (ValueError, KeyError):
                logger.warning(
                    f"[cron_parser] LLM 返回无效 cron: "
                    f"{result['cron_expression']}"
                )
                return None
            return {
                'type': 'cron',
                'cron_expression': result['cron_expression'],
                'human_readable': result.get('human_readable', text),
            }

        elif result.get('type') == 'once' and result.get('scheduled_at'):
            # 验证时间格式
            try:
                dt = datetime.fromisoformat(result['scheduled_at'])
            except ValueError:
                return None
            return {
                'type': 'once',
                'scheduled_at': dt.isoformat(),
                'human_readable': result.get('human_readable', text),
            }

        elif result.get('type') == 'error':
            return result

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"[cron_parser] LLM 返回非 JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"[cron_parser] LLM 解析失败: {e}")
        return None


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
