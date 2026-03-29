"""
LLM 弹性调用模块 — 截断扩容、智能重试、超时保护

封装 resilient_chat() 函数，统一处理：
1. 响应截断检测 + max_tokens 自动扩容
2. LLM 重复输出检测
3. 智能错误分类（上下文超限快速失败、429 指数退避、一般错误重试）
4. 同步超时保护（主线程 signal.SIGALRM / 非主线程 concurrent.futures）

来源：37.32 MiroThinker 特性改造
"""
import concurrent.futures
import logging
import os
import signal
import threading
import time
from contextlib import contextmanager
from typing import Tuple

logger = logging.getLogger(__name__)

# 默认配置（可通过环境变量覆盖）
DEFAULT_LLM_TIMEOUT = int(os.environ.get('LLM_CALL_TIMEOUT', '180'))
DEFAULT_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', '3'))
DEFAULT_BASE_WAIT = float(os.environ.get('LLM_RETRY_BASE_WAIT', '5'))
DEFAULT_MAX_WAIT = float(os.environ.get('LLM_RETRY_MAX_WAIT', '60'))
DEFAULT_EXPAND_RATIO = float(os.environ.get('LLM_TRUNCATION_EXPAND_RATIO', '1.1'))

# 重复检测参数
REPEAT_TAIL_LENGTH = 50
REPEAT_THRESHOLD = 5


# ============ 自定义异常 ============

class LLMCallTimeout(Exception):
    """LLM 调用超时"""
    pass


class ContextLengthExceeded(Exception):
    """上下文长度超限"""
    pass


# ============ 辅助函数 ============

def is_truncated(response) -> bool:
    """
    检测 LangChain 响应是否被截断。

    支持 OpenAI (finish_reason="length") 和 Anthropic (stop_reason="max_tokens") 格式。
    """
    if not hasattr(response, "response_metadata"):
        return False
    meta = response.response_metadata or {}
    if meta.get("finish_reason") == "length":
        return True
    if meta.get("stop_reason") == "max_tokens":
        return True
    return False


def is_repeated(content: str) -> bool:
    """
    检测 LLM 输出是否存在严重重复。

    规则：最后 REPEAT_TAIL_LENGTH 个字符在整个响应中出现超过 REPEAT_THRESHOLD 次。
    """
    if not content or len(content) < REPEAT_TAIL_LENGTH * 2:
        return False
    tail = content[-REPEAT_TAIL_LENGTH:]
    count = content.count(tail)
    return count > REPEAT_THRESHOLD


def is_context_length_error(error: Exception) -> bool:
    """检测是否为上下文长度超限错误"""
    msg = str(error).lower()
    patterns = [
        "maximum context length",
        "context_length_exceeded",
        "max_tokens",
        "longer than the model",
        "too many tokens",
        "prompt is too long",
    ]
    return any(p in msg for p in patterns)


@contextmanager
def timeout_guard(seconds: int):
    """
    同步超时保护。

    主线程使用 signal.SIGALRM（Unix/macOS），
    非主线程使用 concurrent.futures 线程池兜底。
    """
    if not hasattr(signal, 'SIGALRM') or threading.current_thread() is not threading.main_thread():
        # Windows 或非主线程：使用 threading.Timer 兜底
        # 通过设置一个标志位，在超时后让调用方感知
        # 但由于无法中断阻塞的 I/O，这里用 concurrent.futures 包装
        yield
        return

    def handler(signum, frame):
        raise LLMCallTimeout(f"LLM 调用超时 ({seconds}s)")

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def _get_max_tokens(model) -> int:
    """从 LangChain model 获取当前 max_tokens"""
    # ChatOpenAI 用 max_tokens, ChatGoogleGenerativeAI 用 max_output_tokens
    for attr in ("max_tokens", "max_output_tokens"):
        val = getattr(model, attr, None)
        if val is not None:
            return val
    return 4096


def _set_max_tokens(model, new_max: int):
    """创建新的 model 副本，设置新的 max_tokens"""
    try:
        return model.bind(max_tokens=new_max)
    except Exception:
        model.max_tokens = new_max
        return model


def _extract_token_usage(response):
    """从 LangChain 响应中提取 token 用量，失败返回 None"""
    try:
        from utils.token_tracker import extract_token_usage_from_langchain
        return extract_token_usage_from_langchain(response)
    except Exception:
        return None


def resilient_chat(
    model,
    messages: list,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_wait: float = DEFAULT_BASE_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    timeout: int = DEFAULT_LLM_TIMEOUT,
    expand_ratio: float = DEFAULT_EXPAND_RATIO,
    caller: str = "",
) -> Tuple[str, dict]:
    """
    带截断扩容、重复检测、智能重试、超时保护的 LLM 调用。

    Returns:
        (content, metadata) 元组
        metadata: {"finish_reason": str, "truncated": bool, "attempts": int, "token_usage": TokenUsage|None}
    """
    label = f"[{caller}] " if caller else ""
    current_model = model

    _in_main_thread = (
        hasattr(signal, 'SIGALRM')
        and threading.current_thread() is threading.main_thread()
    )

    for attempt in range(max_retries):
        attempts = attempt + 1
        try:
            if _in_main_thread:
                # 主线程：signal.SIGALRM 可以中断阻塞 I/O
                with timeout_guard(timeout):
                    _rate_limit_hook()
                    response = current_model.invoke(messages)
            else:
                # 非主线程：用 concurrent.futures 做超时保护
                _rate_limit_hook()
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = pool.submit(current_model.invoke, messages)
                try:
                    response = future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    future.cancel()
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise LLMCallTimeout(f"LLM 调用超时 ({timeout}s)")
                finally:
                    pool.shutdown(wait=False)

            content = response.content.strip() if response.content else ""

            # --- 提取 token 用量 ---
            token_usage = _extract_token_usage(response)

            # --- 截断检测 ---
            if is_truncated(response):
                if attempt < max_retries - 1:
                    current_max = _get_max_tokens(current_model)
                    new_max = int(current_max * expand_ratio)
                    current_model = _set_max_tokens(model, new_max)
                    logger.warning(
                        f"{label}响应被截断 (attempt {attempts}/{max_retries})，"
                        f"max_tokens {current_max} -> {new_max}，重试中..."
                    )
                    time.sleep(base_wait)
                    continue
                else:
                    logger.warning(f"{label}响应仍被截断 (已重试 {max_retries} 次)，返回截断结果")
                    return content, {"finish_reason": "length", "truncated": True, "attempts": attempts, "token_usage": token_usage}

            # --- 重复检测 ---
            if is_repeated(content):
                if attempt < max_retries - 1:
                    logger.warning(f"{label}检测到重复输出 (attempt {attempts}/{max_retries})，重试中...")
                    time.sleep(base_wait)
                    continue
                else:
                    logger.warning(f"{label}重复输出仍存在 (已重试 {max_retries} 次)，返回当前结果")

            # --- 正常完成 ---
            return content, {"finish_reason": "stop", "truncated": False, "attempts": attempts, "token_usage": token_usage}

        except LLMCallTimeout:
            if attempt < max_retries - 1:
                wait = min(base_wait * (2 ** attempt), max_wait)
                logger.warning(f"{label}LLM 调用超时 ({timeout}s)，等待 {wait:.0f}s 后重试 (attempt {attempts}/{max_retries})")
                time.sleep(wait)
                continue
            else:
                logger.error(f"{label}LLM 调用超时，已重试 {max_retries} 次")
                raise

        except Exception as e:
            # 上下文超限 → 快速失败
            if is_context_length_error(e):
                logger.error(f"{label}上下文长度超限，不重试: {e}")
                raise ContextLengthExceeded(str(e)) from e

            # 429 速率限制 → 指数退避
            if '429' in str(e):
                if attempt < max_retries - 1:
                    wait = min(base_wait * (2 ** attempt), max_wait)
                    logger.warning(f"{label}429 速率限制，等待 {wait:.0f}s 后重试 (attempt {attempts}/{max_retries})")
                    time.sleep(wait)
                    continue
                else:
                    logger.error(f"{label}429 速率限制，已重试 {max_retries} 次")
                    raise

            # 一般错误 → 重试
            if attempt < max_retries - 1:
                wait = min(base_wait * (2 ** attempt), max_wait)
                logger.warning(f"{label}LLM 调用失败: {e}，等待 {wait:.0f}s 后重试 (attempt {attempts}/{max_retries})")
                time.sleep(wait)
                continue
            else:
                logger.error(f"{label}LLM 调用最终失败 (已重试 {max_retries} 次): {e}")
                raise

    raise RuntimeError(f"resilient_chat: 超过最大重试次数 {max_retries}")


# 限流钩子 — 默认使用 llm_service 的 _rate_limit，可被测试替换
def _rate_limit_hook():
    """调用全局限流器"""
    try:
        from services.llm_service import _rate_limit
        _rate_limit()
    except ImportError:
        pass
