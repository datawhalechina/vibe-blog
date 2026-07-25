import importlib


MODULE_ALIASES = (
    ("services.image_service", "services.media.image_service"),
    ("services.video_service", "services.media.video_service"),
    ("services.video_sequence_service", "services.media.video_sequence_service"),
    ("services.sora2_service", "services.media.sora2_service"),
    ("services.image_styles", "services.media.image_styles"),
    ("services.image_styles.manager", "services.media.image_styles.manager"),
    (
        "services.image_styles.type_signals",
        "services.media.image_styles.type_signals",
    ),
)


def test_media_package_is_importable():
    assert importlib.import_module("services.media")


def test_legacy_media_modules_alias_new_modules():
    for legacy_name, current_name in MODULE_ALIASES:
        legacy = importlib.import_module(legacy_name)
        current = importlib.import_module(current_name)

        assert legacy is current, f"{legacy_name} does not alias {current_name}"


def test_media_package_exposes_existing_public_services():
    package = importlib.import_module("services.media")
    image = importlib.import_module("services.media.image_service")
    video = importlib.import_module("services.media.video_service")

    assert package.NanoBananaService is image.NanoBananaService
    assert package.get_image_service is image.get_image_service
    assert package.Veo3Service is video.Veo3Service
    assert package.get_video_service is video.get_video_service


def test_image_style_templates_still_resolve_after_package_move():
    manager = importlib.import_module("services.media.image_styles.manager")

    assert manager.STYLES_CONFIG.is_file()
