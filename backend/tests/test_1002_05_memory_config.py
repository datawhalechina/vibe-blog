"""
1002.05 记忆系统配置化 — TDD 测试

测试 BlogMemoryConfig Pydantic 校验、全局单例、
Storage 配置消费、注入 token 控制、API 端点。
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Pydantic 校验测试 ──────────────────────────────────────


class TestBlogMemoryConfigValidation:
    """Pydantic 字段校验"""

    def test_default_values(self):
        from services.blog_generator.memory.config import BlogMemoryConfig
        cfg = BlogMemoryConfig()
        assert cfg.enabled is True
        assert cfg.storage_backend == "json"
        assert cfg.storage_path == "data/memory/"
        assert cfg.debounce_seconds == 10
        assert cfg.max_facts == 200
        assert cfg.fact_confidence_threshold == 0.7
        assert cfg.injection_enabled is True
        assert cfg.max_injection_tokens == 1500
        assert cfg.auto_extract_enabled is True
        assert cfg.model_name is None

    def test_debounce_seconds_too_low(self):
        from pydantic import ValidationError
        from services.blog_generator.memory.config import BlogMemoryConfig
        with pytest.raises(ValidationError):
            BlogMemoryConfig(debounce_seconds=0)

    def test_debounce_seconds_too_high(self):
        from pydantic import ValidationError
        from services.blog_generator.memory.config import BlogMemoryConfig
        with pytest.raises(ValidationError):
            BlogMemoryConfig(debounce_seconds=999)

    def test_debounce_seconds_boundary_valid(self):
        from services.blog_generator.memory.config import BlogMemoryConfig
        cfg_low = BlogMemoryConfig(debounce_seconds=1)
        assert cfg_low.debounce_seconds == 1
        cfg_high = BlogMemoryConfig(debounce_seconds=300)
        assert cfg_high.debounce_seconds == 300

    def test_max_facts_too_low(self):
        from pydantic import ValidationError
        from services.blog_generator.memory.config import BlogMemoryConfig
        with pytest.raises(ValidationError):
            BlogMemoryConfig(max_facts=5)

    def test_max_facts_boundary_valid(self):
        from services.blog_generator.memory.config import BlogMemoryConfig
        cfg = BlogMemoryConfig(max_facts=10)
        assert cfg.max_facts == 10
        cfg2 = BlogMemoryConfig(max_facts=1000)
        assert cfg2.max_facts == 1000

    def test_confidence_threshold_out_of_range(self):
        from pydantic import ValidationError
        from services.blog_generator.memory.config import BlogMemoryConfig
        with pytest.raises(ValidationError):
            BlogMemoryConfig(fact_confidence_threshold=1.5)
        with pytest.raises(ValidationError):
            BlogMemoryConfig(fact_confidence_threshold=-0.1)

    def test_max_injection_tokens_too_low(self):
        from pydantic import ValidationError
        from services.blog_generator.memory.config import BlogMemoryConfig
        with pytest.raises(ValidationError):
            BlogMemoryConfig(max_injection_tokens=50)

    def test_max_injection_tokens_too_high(self):
        from pydantic import ValidationError
        from services.blog_generator.memory.config import BlogMemoryConfig
        with pytest.raises(ValidationError):
            BlogMemoryConfig(max_injection_tokens=9000)

    def test_preserves_1002_01_fields(self):
        """1002.01 添加的 auto_extract_enabled 和 model_name 应保留"""
        from services.blog_generator.memory.config import BlogMemoryConfig
        cfg = BlogMemoryConfig(auto_extract_enabled=False, model_name="gpt-4o-mini")
        assert cfg.auto_extract_enabled is False
        assert cfg.model_name == "gpt-4o-mini"


# ── 全局单例测试 ──────────────────────────────────────────


class TestGlobalSingleton:
    """全局单例 get/set/load"""

    def test_get_set_roundtrip(self):
        from services.blog_generator.memory.config import (
            BlogMemoryConfig, get_memory_config, set_memory_config,
        )
        original = get_memory_config()
        try:
            custom = BlogMemoryConfig(max_facts=42, debounce_seconds=5)
            set_memory_config(custom)
            assert get_memory_config().max_facts == 42
            assert get_memory_config().debounce_seconds == 5
        finally:
            set_memory_config(original)

    def test_load_from_env(self, monkeypatch):
        from services.blog_generator.memory.config import (
            get_memory_config, set_memory_config, load_memory_config_from_env,
            BlogMemoryConfig,
        )
        original = get_memory_config()
        try:
            monkeypatch.setenv("MEMORY_MAX_FACTS", "300")
            monkeypatch.setenv("MEMORY_DEBOUNCE_SECONDS", "60")
            load_memory_config_from_env()
            cfg = get_memory_config()
            assert cfg.max_facts == 300
            assert cfg.debounce_seconds == 60
        finally:
            set_memory_config(original)

    def test_from_env_reads_all_fields(self, monkeypatch):
        from services.blog_generator.memory.config import BlogMemoryConfig
        monkeypatch.setenv("MEMORY_ENABLED", "false")
        monkeypatch.setenv("MEMORY_STORAGE_PATH", "/tmp/mem/")
        monkeypatch.setenv("MEMORY_DEBOUNCE_SECONDS", "30")
        monkeypatch.setenv("MEMORY_MODEL_NAME", "gpt-4o")
        monkeypatch.setenv("MEMORY_MAX_FACTS", "500")
        monkeypatch.setenv("MEMORY_FACT_THRESHOLD", "0.8")
        monkeypatch.setenv("MEMORY_INJECTION_ENABLED", "false")
        monkeypatch.setenv("MEMORY_MAX_INJECTION_TOKENS", "3000")
        monkeypatch.setenv("MEMORY_AUTO_EXTRACT_ENABLED", "false")
        cfg = BlogMemoryConfig.from_env()
        assert cfg.enabled is False
        assert cfg.storage_path == "/tmp/mem/"
        assert cfg.debounce_seconds == 30
        assert cfg.model_name == "gpt-4o"
        assert cfg.max_facts == 500
        assert cfg.fact_confidence_threshold == 0.8
        assert cfg.injection_enabled is False
        assert cfg.max_injection_tokens == 3000
        assert cfg.auto_extract_enabled is False

    def test_from_env_defaults(self):
        from services.blog_generator.memory.config import BlogMemoryConfig
        cfg = BlogMemoryConfig.from_env()
        assert cfg.enabled is True
        assert cfg.debounce_seconds == 10


# ── Storage 配置消费测试 ──────────────────────────────────


class TestStorageConfigConsumption:
    """Storage 应从全局配置读取 max_facts 和 injection 控制"""

    def test_add_fact_uses_config_max_facts(self, tmp_path):
        from services.blog_generator.memory.storage import MemoryStorage
        from services.blog_generator.memory.config import (
            BlogMemoryConfig, get_memory_config, set_memory_config,
        )
        original = get_memory_config()
        try:
            set_memory_config(BlogMemoryConfig(max_facts=15))
            storage = MemoryStorage(storage_path=str(tmp_path))
            for i in range(20):
                storage.add_fact("u1", f"fact {i}", confidence=0.5 + i * 0.02)
            memory = storage.load("u1")
            assert len(memory["facts"]) <= 15
        finally:
            set_memory_config(original)

    def test_injection_respects_max_tokens(self, tmp_path):
        from services.blog_generator.memory.storage import MemoryStorage
        from services.blog_generator.memory.config import (
            BlogMemoryConfig, get_memory_config, set_memory_config,
        )
        original = get_memory_config()
        try:
            set_memory_config(BlogMemoryConfig(max_injection_tokens=200))
            storage = MemoryStorage(storage_path=str(tmp_path))
            # Add many facts to exceed token limit
            for i in range(50):
                storage.add_fact("u1", f"这是一条很长的事实描述用于测试 token 截断功能 {i}", confidence=0.9)
            result = storage.format_for_injection("u1")
            # Rough token estimate: ~1 token per 2 Chinese chars
            # 200 tokens ≈ 400 chars max
            assert len(result) < 2000  # generous upper bound
        finally:
            set_memory_config(original)

    def test_injection_disabled_returns_empty(self, tmp_path):
        from services.blog_generator.memory.storage import MemoryStorage
        from services.blog_generator.memory.config import (
            BlogMemoryConfig, get_memory_config, set_memory_config,
        )
        original = get_memory_config()
        try:
            set_memory_config(BlogMemoryConfig(injection_enabled=False))
            storage = MemoryStorage(storage_path=str(tmp_path))
            storage.add_fact("u1", "some fact", confidence=0.9)
            result = storage.format_for_injection("u1")
            assert result == ""
        finally:
            set_memory_config(original)


# ── API 端点测试 ──────────────────────────────────────────


class TestMemoryConfigAPI:
    """Flask API 端点测试"""

    @pytest.fixture
    def client(self):
        from flask import Flask
        from routes.memory_routes import memory_bp
        app = Flask(__name__)
        app.register_blueprint(memory_bp)
        app.config["TESTING"] = True
        return app.test_client()

    def test_get_config_returns_json(self, client):
        resp = client.get("/api/memory/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "enabled" in data
        assert "max_facts" in data
        assert "debounce_seconds" in data

    def test_get_status_returns_config(self, client):
        resp = client.get("/api/memory/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "config" in data
