from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def test_feishu_production_modules_are_removed():
    assert not (BACKEND_ROOT / "api/routes/feishu_routes.py").exists()
    assert not (BACKEND_ROOT / "routes/feishu_routes.py").exists()


def test_route_registry_does_not_register_feishu():
    registry = (BACKEND_ROOT / "api/routes/__init__.py").read_text(encoding="utf-8")

    assert "feishu_bp" not in registry
    assert "feishu_routes" not in registry


def test_deployment_configuration_does_not_expose_feishu():
    deployment_files = [
        PROJECT_ROOT / "docker/docker-compose.yml",
        BACKEND_ROOT / ".env.example",
    ]

    for deployment_file in deployment_files:
        contents = deployment_file.read_text(encoding="utf-8")
        assert "FEISHU_" not in contents
        assert "飞书" not in contents


def test_chat_and_whatsapp_boundaries_remain_available():
    registry = (BACKEND_ROOT / "api/routes/__init__.py").read_text(encoding="utf-8")

    assert "chat_bp" in registry
    assert (BACKEND_ROOT / "api/routes/chat_routes.py").is_file()
    assert (BACKEND_ROOT / "services/chat").is_dir()
    assert (PROJECT_ROOT / "integrations/whatsapp-gateway/src/index.js").is_file()
