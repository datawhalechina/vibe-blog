"""
指数退避计算

对应 OpenClaw: src/cron/service/timer.ts L30-41
连续失败时逐步增大重试间隔，防止 retry storm。
"""

ERROR_BACKOFF_SCHEDULE = [
    30,        # 1st error  →  30 秒
    60,        # 2nd error  →   1 分钟
    5 * 60,    # 3rd error  →   5 分钟
    15 * 60,   # 4th error  →  15 分钟
    60 * 60,   # 5th+ error →  60 分钟
]


def error_backoff_seconds(consecutive_errors: int) -> int:
    """根据连续错误次数返回退避秒数"""
    if consecutive_errors <= 0:
        return 0
    idx = min(consecutive_errors - 1, len(ERROR_BACKOFF_SCHEDULE) - 1)
    return ERROR_BACKOFF_SCHEDULE[idx]
