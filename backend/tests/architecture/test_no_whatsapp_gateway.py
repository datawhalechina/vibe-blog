from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def test_whatsapp_gateway_is_removed():
    assert not (PROJECT_ROOT / "integrations/whatsapp-gateway").exists()


def test_local_startup_has_no_whatsapp_hooks():
    start_script = (PROJECT_ROOT / "docker/start-local.sh").read_text(
        encoding="utf-8"
    )

    assert "whatsapp" not in start_script.lower()
    assert "ENABLE_WHATSAPP" not in start_script
    assert "WHATSAPP_DIR" not in start_script


def test_gitignore_has_no_whatsapp_runtime_paths():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "whatsapp" not in gitignore.lower()


def test_chat_api_boundary_remains_available():
    from flask import Flask

    from api.routes import register_all_blueprints

    app = Flask(__name__)
    register_all_blueprints(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    chat_routes = (BACKEND_ROOT / "api/routes/chat_routes.py").read_text(
        encoding="utf-8"
    )

    assert any(rule.startswith("/api/chat/") for rule in rules)
    assert (BACKEND_ROOT / "api/routes/chat_routes.py").is_file()
    assert (BACKEND_ROOT / "services/chat").is_dir()
    assert "X-User-Id" in chat_routes
