"""
多提供商 LLM 客户端工厂

根据 provider 配置自动创建对应的 LangChain ChatModel 实例。
支持 OpenAI / Anthropic / 通义千问 / DeepSeek / 智谱。

来源：37.29 多提供商 LLM 客户端工厂方案
"""

import logging
import os
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

# 延迟导入，避免未安装的包导致启动失败
ChatOpenAI = None
ChatAnthropic = None


def _ensure_openai():
    global ChatOpenAI
    if ChatOpenAI is None:
        from langchain_openai import ChatOpenAI as _cls
        ChatOpenAI = _cls


def _ensure_anthropic():
    global ChatAnthropic
    if ChatAnthropic is None:
        from langchain_anthropic import ChatAnthropic as _cls
        ChatAnthropic = _cls


# ============ 提供商配置 ============

PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    'openai': {
        'env_key': 'OPENAI_API_KEY',
        'type': 'openai',
    },
    'anthropic': {
        'env_key': 'ANTHROPIC_API_KEY',
        'type': 'anthropic',
    },
    'deepseek': {
        'env_key': 'DEEPSEEK_API_KEY',
        'type': 'openai',
        'base_url': 'https://api.deepseek.com',
    },
    'qwen': {
        'env_key': 'DASHSCOPE_API_KEY',
        'type': 'openai',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    },
    'zhipu': {
        'env_key': 'ZHIPU_API_KEY',
        'type': 'openai',
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
    },
}

# ============ 模型白名单 ============

ALLOWED_MODELS = {
    ('openai', 'gpt-4o'),
    ('openai', 'gpt-4o-mini'),
    ('openai', 'o3-mini'),
    ('anthropic', 'claude-sonnet-4-20250514'),
    ('anthropic', 'claude-3-5-sonnet-20241022'),
    ('deepseek', 'deepseek-chat'),
    ('deepseek', 'deepseek-reasoner'),
    ('qwen', 'qwen3-235b-a22b'),
    ('qwen', 'qwen3-30b-a3b'),
    ('qwen', 'qwen3-max'),
    ('qwen', 'qwen3-max-preview'),
    ('zhipu', 'glm-4-plus'),
    ('zhipu', 'glm-4'),
}

# ============ 预设模型列表 ============

AVAILABLE_MODELS_PRESET = [
    {'provider': 'anthropic', 'model_name': 'claude-sonnet-4-20250514',
     'display_name': 'Claude 4 Sonnet', 'category': 'recommended'},
    {'provider': 'openai', 'model_name': 'gpt-4o',
     'display_name': 'GPT-4o', 'category': 'recommended'},
    {'provider': 'deepseek', 'model_name': 'deepseek-chat',
     'display_name': 'DeepSeek-V3', 'category': 'budget'},
    {'provider': 'deepseek', 'model_name': 'deepseek-reasoner',
     'display_name': 'DeepSeek-R1', 'category': 'budget'},
    {'provider': 'qwen', 'model_name': 'qwen3-max',
     'display_name': 'Qwen3-Max', 'category': 'chinese'},
    {'provider': 'qwen', 'model_name': 'qwen3-235b-a22b',
     'display_name': 'Qwen3-235B', 'category': 'budget'},
    {'provider': 'zhipu', 'model_name': 'glm-4-plus',
     'display_name': 'GLM-4-Plus', 'category': 'chinese'},
]


# ============ 工厂函数 ============


def create_llm_client(
    provider: str,
    model_name: str,
    api_key: str = None,
    base_url: str = None,
    temperature: float = 0.7,
    max_tokens: int = None,
    **kwargs,
):
    """
    LLM 客户端工厂 — 根据提供商创建 LangChain ChatModel。

    大部分提供商兼容 OpenAI API，只需改 base_url。
    Anthropic 使用独立的 ChatAnthropic。
    """
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"不支持的提供商: {provider}")

    cfg = PROVIDER_CONFIGS[provider]

    # 自动获取 API Key
    if not api_key:
        api_key = os.environ.get(cfg['env_key'], '')
        if not api_key:
            raise ValueError(f"未配置 {cfg['env_key']}，无法使用 {provider}")

    # 自动获取 base_url
    if not base_url:
        base_url = cfg.get('base_url')

    max_tokens = max_tokens or int(os.environ.get('LLM_MAX_TOKENS', '8192'))

    if cfg['type'] == 'anthropic':
        _ensure_anthropic()
        return ChatAnthropic(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        _ensure_openai()
        # 使用不带代理的 httpx 客户端，避免系统代理干扰国内 API（如 dashscope）
        no_proxy_client = httpx.Client(
            proxy=None,
            timeout=httpx.Timeout(timeout=300.0, connect=10.0),
        )
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=2,
            http_client=no_proxy_client,
        )


def validate_model_config(provider: str, model_name: str):
    """验证模型是否在白名单中"""
    if (provider, model_name) not in ALLOWED_MODELS:
        raise ValueError(f"不支持的模型: {provider}/{model_name}")


def get_available_models() -> List[Dict[str, Any]]:
    """返回可用模型列表（根据 API Key 是否配置判断 available）"""
    result = []
    for preset in AVAILABLE_MODELS_PRESET:
        provider = preset['provider']
        cfg = PROVIDER_CONFIGS.get(provider, {})
        env_key = cfg.get('env_key', '')
        available = bool(os.environ.get(env_key, ''))
        result.append({**preset, 'available': available})
    return result