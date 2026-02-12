"""
LLM 服务模块 - 统一管理大模型客户端

"""
import logging
import threading
import time
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

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
    
    def _create_chat_model(self, model_name: str):
        """创建 LangChain ChatModel 实例"""
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
                return ChatOpenAI(
                    model=model_name,
                    api_key=self._openai_api_key,
                    base_url=self._openai_api_base if self._openai_api_base else None,
                    temperature=0.7,
                    max_tokens=self.max_tokens,
                    max_retries=6,
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
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        response_format: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式 [{"role": "user/system/assistant", "content": "..."}]
            temperature: 温度参数
            response_format: 响应格式，如 {"type": "json_object"}
            
        Returns:
            模型响应文本，失败返回 None
        """
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        
        model = self.get_text_model()
        if not model:
            logger.error("模型不可用")
            return None
        
        try:
            # 如果指定了 JSON 格式，尝试绑定到模型（部分 provider 可能不支持）
            if response_format and response_format.get("type") == "json_object":
                try:
                    model = model.bind(response_format={"type": "json_object"})
                except Exception as bind_err:
                    logger.warning(f"模型不支持 response_format 绑定: {bind_err}")

            # 转换消息格式
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

            # 带应用层重试的调用（处理 429 速率限制）
            max_app_retries = 3
            for attempt in range(max_app_retries):
                try:
                    _rate_limit()
                    response = model.invoke(langchain_messages)
                    return response.content.strip()
                except Exception as invoke_err:
                    if '429' in str(invoke_err) and attempt < max_app_retries - 1:
                        wait = (attempt + 1) * 5  # 5s, 10s
                        logger.warning(f"LLM 429 速率限制，等待 {wait}s 后重试 (attempt {attempt + 1}/{max_app_retries})")
                        time.sleep(wait)
                    else:
                        raise invoke_err
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
    
    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        on_chunk: callable = None,
        response_format: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        发送流式聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            on_chunk: 每收到一个 chunk 时的回调函数 (delta, accumulated)
            response_format: 响应格式，如 {"type": "json_object"}

        Returns:
            完整的模型响应文本，失败返回 None
        """
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        model = self.get_text_model()
        if not model:
            logger.error("模型不可用")
            return None

        try:
            # 如果指定了 JSON 格式，尝试绑定到模型（部分 provider 可能不支持）
            if response_format and response_format.get("type") == "json_object":
                try:
                    model = model.bind(response_format={"type": "json_object"})
                except Exception as bind_err:
                    logger.warning(f"模型不支持 response_format 绑定: {bind_err}")
            # 转换消息格式
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

            # 带应用层重试的流式调用
            max_app_retries = 3
            for attempt in range(max_app_retries):
                try:
                    _rate_limit()
                    full_content = ""
                    for chunk in model.stream(langchain_messages):
                        delta = chunk.content if hasattr(chunk, 'content') else str(chunk)
                        full_content += delta
                        if on_chunk:
                            on_chunk(delta, full_content)
                    return full_content.strip()
                except Exception as stream_err:
                    if '429' in str(stream_err) and attempt < max_app_retries - 1:
                        wait = (attempt + 1) * 5
                        logger.warning(f"LLM 流式 429 速率限制，等待 {wait}s 后重试 (attempt {attempt + 1}/{max_app_retries})")
                        time.sleep(wait)
                    else:
                        raise stream_err
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
