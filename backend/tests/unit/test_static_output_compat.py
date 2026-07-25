import pytest
from flask import Flask

from routes.static_routes import static_bp


def _app(current_output, legacy_output):
    app = Flask(__name__)
    app.config.update(
        OUTPUT_FOLDER=str(current_output),
        LEGACY_OUTPUT_FOLDER=str(legacy_output),
    )
    app.register_blueprint(static_bp)
    return app


def test_output_route_prefers_runtime_file(tmp_path):
    current = tmp_path / "var" / "outputs"
    legacy = tmp_path / "backend" / "outputs"
    (current / "images").mkdir(parents=True)
    (legacy / "images").mkdir(parents=True)
    (current / "images" / "cover.txt").write_text("current", encoding="utf-8")
    (legacy / "images" / "cover.txt").write_text("legacy", encoding="utf-8")

    response = _app(current, legacy).test_client().get("/outputs/images/cover.txt")

    assert response.status_code == 200
    assert response.text == "current"


def test_output_route_falls_back_to_legacy_file(tmp_path):
    current = tmp_path / "var" / "outputs"
    legacy = tmp_path / "backend" / "outputs"
    (legacy / "covers").mkdir(parents=True)
    (legacy / "covers" / "cover.txt").write_text("legacy", encoding="utf-8")

    response = _app(current, legacy).test_client().get("/outputs/covers/cover.txt")

    assert response.status_code == 200
    assert response.text == "legacy"


def test_legacy_xhs_page_redirects_to_vue_route(tmp_path):
    response = _app(tmp_path / "outputs", tmp_path / "legacy").test_client().get(
        "/xhs.html"
    )

    assert response.status_code == 308
    assert response.headers["Location"] == "/xhs"


@pytest.mark.parametrize(
    "path",
    (
        "/",
        "/reviewer",
        "/home.md",
        "/_sidebar.md",
        "/static/_sidebar.md",
        "/chapter/legacy",
        "/chapter/legacy.md",
        "/static/chapter/legacy",
        "/static/chapter/legacy.md",
    ),
)
def test_removed_legacy_static_routes_return_not_found(tmp_path, path):
    response = _app(tmp_path / "outputs", tmp_path / "legacy").test_client().get(path)

    assert response.status_code == 404


def test_removed_static_chapter_image_alias_returns_not_found(tmp_path):
    current = tmp_path / "outputs"
    (current / "images").mkdir(parents=True)
    (current / "images" / "cover.txt").write_text("current", encoding="utf-8")

    response = _app(current, tmp_path / "legacy").test_client().get(
        "/static/chapter/outputs/images/cover.txt"
    )

    assert response.status_code == 404


def test_supported_static_api_routes_remain_available(tmp_path):
    client = _app(tmp_path / "outputs", tmp_path / "legacy").test_client()

    assert client.get("/api/config").status_code == 200
    assert client.get("/api-docs").status_code == 200
