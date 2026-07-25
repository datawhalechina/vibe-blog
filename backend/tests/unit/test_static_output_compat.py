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
