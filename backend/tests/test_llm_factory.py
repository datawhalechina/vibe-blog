"""
多提供商 LLM 客户端工厂 单元测试
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestProviderConfigs:
    """提供商配置测试"""

    def test_all_providers_have_env_key(self):
        from services.llm_factory import PROVIDER_CONFIGS
        for name, cfg in PROVIDER_CONFIGS.items():
            assert 'env_key' in cfg, f"{name} 缺少 env_key"

    def test_openai_compatible_providers_have_base_url(self):
        from services.llm_factory import PROVIDER_CONFIGS
        for name in ('deepseek', 'zhipu', 'qwen'):
            if name in PROVIDER_CONFIGS:
                assert 'base_url' in PROVIDER_CONFIGS[name], f"{name} 缺少 base_url"

    def test_supported_providers(self):
        from services.llm_factory import PROVIDER_CONFIGS
        assert 'openai' in PROVIDER_CONFIGS
        assert 'anthropic' in PROVIDER_CONFIGS
        assert 'deepseek' in PROVIDER_CONFIGS
        assert 'qwen' in PROVIDER_CONFIGS
        assert 'zhipu' in PROVIDER_CONFIGS


class TestCreateLLMClient:
    """工厂函数测试"""

    @patch('services.llm_factory.ChatOpenAI')
    def test_create_openai_client(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        client = create_llm_client('openai', 'gpt-4o', api_key='sk-test')
        mock_cls.assert_called_once()
        assert client is not None

    @patch('services.llm_factory.ChatOpenAI')
    def test_create_deepseek_client(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        client = create_llm_client('deepseek', 'deepseek-chat', api_key='sk-test')
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert 'deepseek' in call_kwargs.get('base_url', '')

    @patch('services.llm_factory.ChatOpenAI')
    def test_create_qwen_client(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        client = create_llm_client('qwen', 'qwen3-max', api_key='sk-test')
        call_kwargs = mock_cls.call_args[1]
        assert 'dashscope' in call_kwargs.get('base_url', '')

    @patch('services.llm_factory.ChatAnthropic')
    def test_create_anthropic_client(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        client = create_llm_client('anthropic', 'claude-sonnet-4-20250514', api_key='sk-ant-test')
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs['model'] == 'claude-sonnet-4-20250514'

    def test_create_unknown_provider_raises(self):
        from services.llm_factory import create_llm_client
        with pytest.raises(ValueError, match='不支持的提供商'):
            create_llm_client('unknown_provider', 'model-x', api_key='key')

    @patch('services.llm_factory.ChatOpenAI')
    def test_api_key_from_env(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-key'}):
            client = create_llm_client('openai', 'gpt-4o')
            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs['api_key'] == 'env-key'

    def test_no_api_key_raises(self):
        from services.llm_factory import create_llm_client
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('OPENAI_API_KEY', None)
            with pytest.raises(ValueError, match='未配置'):
                create_llm_client('openai', 'gpt-4o')

    @patch('services.llm_factory.ChatOpenAI')
    def test_custom_temperature(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        create_llm_client('openai', 'gpt-4o', api_key='k', temperature=0.3)
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs['temperature'] == 0.3

    @patch('services.llm_factory.ChatOpenAI')
    def test_custom_max_tokens(self, mock_cls):
        from services.llm_factory import create_llm_client
        mock_cls.return_value = MagicMock()
        create_llm_client('openai', 'gpt-4o', api_key='k', max_tokens=16384)
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs['max_tokens'] == 16384


class TestGetAvailableModels:
    """可用模型列表测试"""

    def test_returns_list(self):
        from services.llm_factory import get_available_models
        models = get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_model_structure(self):
        from services.llm_factory import get_available_models
        models = get_available_models()
        for m in models:
            assert 'provider' in m
            assert 'model_name' in m
            assert 'display_name' in m
            assert 'available' in m

    def test_available_reflects_env(self):
        from services.llm_factory import get_available_models
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test'}, clear=False):
            models = get_available_models()
            openai_models = [m for m in models if m['provider'] == 'openai']
            for m in openai_models:
                assert m['available'] is True

    def test_unavailable_without_key(self):
        from services.llm_factory import get_available_models
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            models = get_available_models()
            anthropic_models = [m for m in models if m['provider'] == 'anthropic']
            for m in anthropic_models:
                assert m['available'] is False


class TestValidateModelConfig:
    """模型白名单验证测试"""

    def test_valid_model(self):
        from services.llm_factory import validate_model_config
        # 不应抛异常
        validate_model_config('openai', 'gpt-4o')

    def test_invalid_model_raises(self):
        from services.llm_factory import validate_model_config
        with pytest.raises(ValueError, match='不支持的模型'):
            validate_model_config('openai', 'gpt-999-turbo')
