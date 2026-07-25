from services.image_service import NanoBananaService
from services.video_service import Veo3Service


def test_image_service_defaults_to_runtime_outputs(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBE_RUNTIME_DIR", str(tmp_path / "runtime"))

    service = NanoBananaService(api_key="test")

    assert service.output_folder == str(tmp_path / "runtime" / "outputs" / "images")


def test_video_service_defaults_to_runtime_outputs(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBE_RUNTIME_DIR", str(tmp_path / "runtime"))

    service = Veo3Service(api_key="test")

    assert service.output_folder == str(tmp_path / "runtime" / "outputs" / "videos")


def test_media_services_preserve_output_folder_override(monkeypatch, tmp_path):
    output_root = tmp_path / "mounted-outputs"
    monkeypatch.setenv("OUTPUT_FOLDER", str(output_root))

    image_service = NanoBananaService(api_key="test")
    video_service = Veo3Service(api_key="test")

    assert image_service.output_folder == str(output_root / "images")
    assert video_service.output_folder == str(output_root / "videos")
