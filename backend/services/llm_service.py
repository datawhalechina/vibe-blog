"""
LLM 服务模块 - 统一管理大模型客户端

"""
import logging
import os
import threading
import time
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


def _resolve_caller(caller: str) -> str:
    """解析 caller 标识：优先使用显式传入值，否则从中间件上下文获取当前节点名。"""
    if caller:
        return caller
    try:
        from services.blog_generator.middleware import current_node_name
        node = current_node_name.get("")
        if node:
            return node
    except Exception:
        pass
    return "unknown"

# 全局请求限流器：防止并发请求触发 API 速率限制
_request_lock = threading.Lock()
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = float(__import__('os').environ.get('LLM_MIN_REQUEST_INTERVAL', '1.0'))  # 秒


def _rate_limit():
    """简单的全局限流：确保两次请求之间至少间隔 _MIN_REQUEST_INTERVAL 秒"""
    global _last_request_time
    with _request_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


class LLMService:
    """
    LLM 服务类 - 统一管理文本模型
    
    支持:
    - OpenAI 兼容 API (OpenAI, Azure, 阿里云 DashScope 等)
    - Google Gemini
    """
    
    def __init__(
        self,
        provider_format: str = "openai",
        openai_api_key: str = "",
        openai_api_base: str = "",
        google_api_key: str = "",
        text_model: str = "gpt-4o",
        max_tokens: int = None,
    ):
        """
        初始化 LLM 服务

        Args:
            provider_format: AI Provider 格式 ('openai' 或 'gemini')
            openai_api_key: OpenAI 兼容 API Key
            openai_api_base: OpenAI 兼容 API 基础 URL
            google_api_key: Google API Key
            text_model: 文本生成模型名称
            max_tokens: 最大输出 token 数 (默认 None 使用环境变量或 8192)
        """
        self.provider_format = provider_format.lower()
        self._openai_api_key = openai_api_key
        self._openai_api_base = openai_api_base
        self._google_api_key = google_api_key
        self.text_model = text_model

        import os
        self.max_tokens = max_tokens or int(os.environ.get('LLM_MAX_TOKENS', '8192'))

        # 懒加载的模型实例
        self._text_chat_model = None

        # Token 追踪器（由 BlogGenerator 注入，默认 None）
        self.token_tracker = None

        # SSE 事件推送（由 BlogService 注入，默认 None）
        self.task_manager = None
        self.task_id = None
    
    def _create_chat_model(self, model_name: str):
        """创建 LangChain ChatModel 实例（优先使用 ClientFactory）"""
        try:
            # 37.29: 尝试通过 ClientFactory 创建（支持多提供商）
            from services.llm_factory import create_llm_client, PROVIDER_CONFIGS
            provider = self.provider_format
            if provider in PROVIDER_CONFIGS:
                return create_llm_client(
                    provider=provider,
                    model_name=model_name,
                    api_key=self._openai_api_key or None,
                    base_url=self._openai_api_base or None,
                    max_tokens=self.max_tokens,
                )
        except (ImportError, ValueError):
            pass
        except Exception as e:
            logger.debug(f"ClientFactory 创建失败，回退原始逻辑: {e}")

        # 回退：原始创建逻辑（gemini 等）
        try:
            if self.provider_format == 'gemini' and self._google_api_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=self._google_api_key,
                    temperature=0.7,
                    max_output_tokens=self.max_tokens
                )
            elif self._openai_api_key:
                from langchain_openai import ChatOpenAI
                no_proxy_client = httpx.Client(
                    proxy=None,
                    timeout=httpx.Timeout(timeout=300.0, connect=10.0),
                )
                return ChatOpenAI(
                    model=model_name,
                    api_key=self._openai_api_key,
                    base_url=self._openai_api_base if self._openai_api_base else None,
                    temperature=0.7,
                    max_tokens=self.max_tokens,
                    max_retries=6,
                    http_client=no_proxy_client,
                )
            else:
                logger.warning(f"未配置有效的 API Key，无法创建模型: {model_name}")
                return None
        except Exception as e:
            logger.error(f"创建模型失败 ({model_name}): {e}")
            return None
    
    def get_text_model(self):
        """获取文本生成模型"""
        if self._text_chat_model is None:
            self._text_chat_model = self._create_chat_model(self.text_model)
        return self._text_chat_model
    
    def is_available(self) -> bool:
        """检查 LLM 服务是否可用"""
        if self.provider_format == 'gemini':
            return bool(self._google_api_key)
        return bool(self._openai_api_key)

    @staticmethod
    def _supports_thinking(model_name: str) -> bool:
        """检查模型是否支持 Extended Thinking（仅 Claude 系列）"""
        if not model_name:
            return False
        return "claude" in model_name.lower()

    def _chat_with_thinking(
        self,
        langchain_messages: list,
        budget_tokens: int = 19000,
        caller: str = "",
    ) -> Optional[str]:
        """使用 Anthropic Extended Thinking 模式调用

        通过 anthropic SDK 直接调用（LangChain 尚未完整支持 thinking 参数）。
        如果 anthropic SDK 不可用，降级为普通调用。
        """
        try:
            import anthropic
        except ImportError:
            logger.warning(f"[{caller}] anthropic SDK 未安装，降级为普通调用")
            return self._chat_with_thinking_fallback(langchain_messages, caller)

        try:
            # 将 LangChain 消息转为 Anthropic API 格式
            api_messages = []
            system_text = ""
            for msg in langchain_messages:
                role = msg.type  # "human" / "system" / "ai"
                content = msg.content
                if role == "system":
                    system_text = content
                elif role == "ai":
                    api_messages.append({"role": "assistant", "content": content})
                else:
                    api_messages.append({"role": "user", "content": content})

            client = anthropic.Anthropic(
                api_key=self._openai_api_key,
                base_url=self._openai_api_base or None,
            )

            kwargs = {
                "model": self.text_model,
                "max_tokens": self.max_tokens + budget_tokens,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": budget_tokens,
                },
                "messages": api_messages,
            }
            if system_text:
                kwargs["system"] = system_text

            _rate_limit()
            response = client.messages.create(**kwargs)

            # 提取最终文本（跳过 thinking blocks）
            text_parts = []
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    text_parts.append(block.text)

            # 记录 thinking token 用量
            if self.token_tracker and response.usage:
                try:
                    from utils.token_tracker import TokenUsage
                    usage = TokenUsage(
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        model=self.text_model,
                        provider="anthropic",
                    )
                    # 记录 thinking tokens（如果 API 返回）
                    thinking_tokens = getattr(response.usage, "cache_creation_input_tokens", 0)
                    if hasattr(response.usage, "thinking_tokens"):
                        thinking_tokens = response.usage.thinking_tokens
                    if thinking_tokens:
                        usage.extra = {"thinking_tokens": thinking_tokens}
                    self.token_tracker.record(usage, agent=_resolve_caller(caller))
                except Exception:
                    pass

            return "\n".join(text_parts).strip() if text_parts else None

        except Exception as e:
            logger.warning(f"[{caller}] Thinking 模式调用失败: {e}，降级为普通调用")
            return self._chat_with_thinking_fallback(langchain_messages, caller)

    def _chat_with_thinking_fallback(self, langchain_messages: list, caller: str) -> Optional[str]:
        """Thinking 模式降级：使用普通 resilient_chat"""
        from utils.resilient_llm_caller import resilient_chat
        model = self.get_text_model()
        if not model:
            return None
        content, _ = resilient_chat(model=model, messages=langchain_messages, caller=caller)
        return content

    @staticmethod
    def _convert_messages(messages: List[Dict[str, Any]]) -> list:
        """将 dict 格式消息转换为 LangChain 消息对象"""
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        return langchain_messages
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        response_format: Dict[str, Any] = None,
        caller: str = "",
        thinking: bool = False,
        thinking_budget: int = 19000,
    ) -> Optional[str]:
        """
        发送聊天请求（带截断扩容、智能重试、超时保护）

        Args:
            messages: 消息列表，格式 [{"role": "user/system/assistant", "content": "..."}]
            temperature: 温度参数
            response_format: 响应格式，如 {"type": "json_object"}
            caller: 调用方标识（用于日志追踪）
            thinking: 是否启用 Extended Thinking 模式（仅 Claude 模型支持）
            thinking_budget: Thinking 模式的 budget_tokens（默认 19000）

        Returns:
            模型响应文本，失败返回 None
        """
        from utils.resilient_llm_caller import resilient_chat, ContextLengthExceeded
        from utils.context_guard import ContextGuard

        model = self.get_text_model()
        if not model:
            logger.error("模型不可用")
            return None

        try:
            # 上下文长度预警（不阻断调用）
            guard = ContextGuard(self.text_model, max_output_tokens=self.max_tokens)
            check = guard.check(messages)
            if not check["is_safe"]:
                logger.warning(
                    f"[{caller}] prompt 超限 {check['overflow_tokens']:,} tokens，"
                    f"建议调用方裁剪内容"
                )
            # 如果指定了 JSON 格式，尝试绑定到模型（部分 provider 可能不支持）
            if response_format and response_format.get("type") == "json_object":
                try:
                    model = model.bind(response_format={"type": "json_object"})
                except Exception as bind_err:
                    logger.warning(f"模型不支持 response_format 绑定: {bind_err}")

            # 转换消息格式
            langchain_messages = self._convert_messages(messages)

            # SSE: 发送 llm_start 事件
            _send_llm = (
                self.task_manager and self.task_id
                and os.environ.get('SSE_LLM_EVENTS_ENABLED', 'true').lower() != 'false'
            )
            start_time = time.time()
            if _send_llm:
                self.task_manager.send_event(self.task_id, 'llm_start', {
                    'agent': caller,
                    'model': self.text_model,
                    'thinking': thinking,
                })

            # Thinking 模式分支
            if thinking and self._supports_thinking(self.text_model):
                content = self._chat_with_thinking(
                    langchain_messages, thinking_budget, caller=caller,
                )
                metadata = {"attempts": 1}
            else:
                if thinking:
                    logger.info(f"[{caller}] 模型 {self.text_model} 不支持 Thinking，降级为普通调用")
                # 使用 resilient_chat 替代原来的简单调用
                content, metadata = resilient_chat(
                    model=model,
                    messages=langchain_messages,
                    caller=caller,
                )

            # SSE: 发送 llm_end 事件
            if _send_llm:
                duration_ms = int((time.time() - start_time) * 1000)
                self.task_manager.send_event(self.task_id, 'llm_end', {
                    'agent': caller,
                    'model': self.text_model,
                    'duration_ms': duration_ms,
                    'truncated': metadata.get('truncated', False),
                    'attempts': metadata.get('attempts', 1),
                    'thinking': thinking,
                })

            if metadata.get("truncated"):
                logger.warning(f"[{caller}] 响应被截断，内容可能不完整")

            # 记录 token 用量
            if self.token_tracker and metadata.get("token_usage"):
                token_usage = metadata["token_usage"]
                token_usage.model = self.text_model
                token_usage.provider = self.provider_format
                self.token_tracker.record(token_usage, agent=_resolve_caller(caller))

            return content

        except ContextLengthExceeded as e:
            logger.error(f"上下文超限: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
    
    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        on_chunk: callable = None,
        response_format: Dict[str, Any] = None,
        caller: str = "",
    ) -> Optional[str]:
        """
        发送流式聊天请求（带超时保护和智能重试）

        Args:
            messages: 消息列表
            temperature: 温度参数
            on_chunk: 每收到一个 chunk 时的回调函数 (delta, accumulated)
            response_format: 响应格式，如 {"type": "json_object"}
            caller: 调用方标识（用于日志追踪）

        Returns:
            完整的模型响应文本，失败返回 None
        """
        from utils.resilient_llm_caller import (
            timeout_guard, is_truncated, is_context_length_error,
            LLMCallTimeout, ContextLengthExceeded,
            DEFAULT_LLM_TIMEOUT, DEFAULT_MAX_RETRIES, DEFAULT_BASE_WAIT, DEFAULT_MAX_WAIT,
        )

        model = self.get_text_model()
        if not model:
            logger.error("模型不可用")
            return None

        try:
            if response_format and response_format.get("type") == "json_object":
                try:
                    model = model.bind(response_format={"type": "json_object"})
                except Exception as bind_err:
                    logger.warning(f"模型不支持 response_format 绑定: {bind_err}")

            langchain_messages = self._convert_messages(messages)
            label = f"[{caller}] " if caller else ""

            for attempt in range(DEFAULT_MAX_RETRIES):
                attempts = attempt + 1
                try:
                    _rate_limit()
                    full_content = ""
                    last_chunk = None
                    with timeout_guard(DEFAULT_LLM_TIMEOUT):
                        for chunk in model.stream(langchain_messages):
                            delta = chunk.content if hasattr(chunk, 'content') else str(chunk)
                            full_content += delta
                            last_chunk = chunk
                            if on_chunk:
                                on_chunk(delta, full_content)

                    # 流式完成后提取 token 用量
                    if self.token_tracker and last_chunk:
                        try:
                            from utils.token_tracker import extract_token_usage_from_langchain
                            token_usage = extract_token_usage_from_langchain(
                                last_chunk, model=self.text_model, provider=self.provider_format
                            )
                            if token_usage.input_tokens or token_usage.output_tokens:
                                self.token_tracker.record(token_usage, agent=_resolve_caller(caller))
                        except Exception:
                            pass

                    return full_content.strip()

                except LLMCallTimeout:
                    if attempt < DEFAULT_MAX_RETRIES - 1:
                        wait = min(DEFAULT_BASE_WAIT * (2 ** attempt), DEFAULT_MAX_WAIT)
                        logger.warning(f"{label}流式调用超时，等待 {wait:.0f}s 后重试 (attempt {attempts}/{DEFAULT_MAX_RETRIES})")
                        time.sleep(wait)
                        continue
                    raise

                except Exception as stream_err:
                    if is_context_length_error(stream_err):
                        raise ContextLengthExceeded(str(stream_err)) from stream_err

                    if '429' in str(stream_err) and attempt < DEFAULT_MAX_RETRIES - 1:
                        wait = min(DEFAULT_BASE_WAIT * (2 ** attempt), DEFAULT_MAX_WAIT)
                        logger.warning(f"{label}流式 429 速率限制，等待 {wait:.0f}s 后重试 (attempt {attempts}/{DEFAULT_MAX_RETRIES})")
                        time.sleep(wait)
                        continue

                    if attempt < DEFAULT_MAX_RETRIES - 1:
                        wait = min(DEFAULT_BASE_WAIT * (2 ** attempt), DEFAULT_MAX_WAIT)
                        logger.warning(f"{label}流式调用失败: {stream_err}，等待 {wait:.0f}s 后重试 (attempt {attempts}/{DEFAULT_MAX_RETRIES})")
                        time.sleep(wait)
                        continue
                    raise

        except ContextLengthExceeded as e:
            logger.error(f"流式调用上下文超限: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            return None
    
    def chat_with_image(
        self,
        prompt: str,
        image_base64: str,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        发送包含图片的聊天请求（多模态）
        
        Args:
            prompt: 文本提示词
            image_base64: Base64 编码的图片数据
            mime_type: 图片 MIME 类型 (image/jpeg, image/png 等)
            
        Returns:
            模型响应文本，失败返回 None
        """
        try:
            from langchain_core.messages import HumanMessage
            
            model = self.get_text_model()
            if not model:
                logger.error("模型不可用")
                return None
            
            # 构建包含图片的消息
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    }
                ]
            )
            
            _rate_limit()
            response = model.invoke([message])
            return response.content.strip() if response else None
            
        except Exception as e:
            logger.warning(f"多模态调用失败: {e}")
            return None


# 全局 LLM 服务实例 (懒加载)
_llm_service: Optional[LLMService] = None


def get_llm_service() -> Optional[LLMService]:
    """获取全局 LLM 服务实例"""
    return _llm_service


def init_llm_service(config: dict) -> LLMService:
    """
    从配置初始化 LLM 服务
    
    Args:
        config: Flask app.config 字典
        
    Returns:
        LLMService 实例
    """
    global _llm_service
    _llm_service = LLMService(
        provider_format=config.get('AI_PROVIDER_FORMAT', 'openai'),
        openai_api_key=config.get('OPENAI_API_KEY', ''),
        openai_api_base=config.get('OPENAI_API_BASE', ''),
        google_api_key=config.get('GOOGLE_API_KEY', ''),
        text_model=config.get('TEXT_MODEL', 'gpt-4o'),
    )
    logger.info(f"LLM 服务已初始化: provider={_llm_service.provider_format}, text_model={_llm_service.text_model}")
    return _llm_service
