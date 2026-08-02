import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.blog_generator.lifecycle.media_pipeline import (
    ANIMATION_PROMPT,
    generate_cover_image,
    generate_cover_video,
    generate_sequence_video,
    merge_videos,
)


MEDIA_FUNCTIONS = (
    generate_cover_image,
    generate_cover_video,
    generate_sequence_video,
    merge_videos,
)


def test_media_functions_use_explicit_keyword_dependencies():
    for function in MEDIA_FUNCTIONS:
        signature = inspect.signature(function)
        assert all(
            parameter.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD
            for parameter in signature.parameters.values()
        )
        assert not {"service", "context", "generator"} & set(signature.parameters)


def test_cover_image_unavailable_returns_none_without_summarizing():
    image_service = MagicMock()
    image_service.is_available.return_value = False
    summarize = MagicMock()

    result = generate_cover_image(
        title="Title",
        topic="Topic",
        full_content="# Body",
        llm_client=object(),
        image_service=image_service,
        summarize=summarize,
        render_style_prompt=MagicMock(),
        render_default_prompt=MagicMock(),
    )

    assert result is None
    summarize.assert_not_called()


def test_cover_image_uses_summary_fallback_portrait_and_existing_events():
    image_service = MagicMock()
    image_service.is_available.return_value = True
    image_service.generate.return_value = SimpleNamespace(
        oss_url="https://cdn.example/cover.png",
        local_path="/tmp/cover.png",
        url="https://provider.example/cover.png",
    )
    events = []
    render_default_prompt = MagicMock(return_value="cover prompt")

    result = generate_cover_image(
        title="Title",
        topic="Topic",
        full_content="# Body",
        llm_client=object(),
        image_service=image_service,
        summarize=MagicMock(return_value=""),
        render_style_prompt=MagicMock(),
        render_default_prompt=render_default_prompt,
        emit_event=lambda name, payload: events.append((name, payload)),
        video_aspect_ratio="9:16",
    )

    assert result == (
        "https://cdn.example/cover.png",
        "https://cdn.example/cover.png",
        "标题：Title\n主题：Topic",
    )
    render_default_prompt.assert_called_once_with("标题：Title\n主题：Topic")
    call = image_service.generate.call_args
    assert call.kwargs["aspect_ratio"].value == "9:16"
    assert call.kwargs["download"] is True
    assert [payload["message"] for name, payload in events if name == "log"] == [
        "正在提炼文章摘要...",
        "正在生成封面架构图...",
        "封面架构图生成完成",
    ]


def test_cover_image_uses_style_renderer_when_selected():
    image_service = MagicMock()
    image_service.is_available.return_value = True
    image_service.generate.return_value = SimpleNamespace(
        oss_url=None,
        local_path="/tmp/cover.png",
        url="https://provider.example/cover.png",
    )
    render_style_prompt = MagicMock(return_value="styled prompt")
    render_default_prompt = MagicMock()

    result = generate_cover_image(
        title="Title",
        topic="Topic",
        full_content="# Body",
        llm_client=object(),
        image_service=image_service,
        summarize=MagicMock(return_value="Summary"),
        render_style_prompt=render_style_prompt,
        render_default_prompt=render_default_prompt,
        image_style="academic",
    )

    assert result == (
        "https://provider.example/cover.png",
        "/tmp/cover.png",
        "Summary",
    )
    render_style_prompt.assert_called_once_with("academic", "Summary")
    render_default_prompt.assert_not_called()


def test_cover_image_exception_degrades_to_none():
    image_service = MagicMock()
    image_service.is_available.return_value = True

    assert generate_cover_image(
        title="Title",
        topic="Topic",
        full_content="# Body",
        llm_client=object(),
        image_service=image_service,
        summarize=MagicMock(side_effect=RuntimeError("provider unavailable")),
        render_style_prompt=MagicMock(),
        render_default_prompt=MagicMock(),
    ) is None


def test_cover_video_unavailable_preserves_progress_events():
    video_service = MagicMock()
    video_service.is_available.return_value = False
    events = []

    result = generate_cover_video(
        cover_image_url="https://example.com/cover.png",
        section_images=[],
        get_video_service=MagicMock(return_value=video_service),
        get_oss_service=MagicMock(),
        emit_event=lambda name, payload: events.append((name, payload)),
    )

    assert result is None
    assert events[:2] == [
        (
            "progress",
            {"stage": "video", "progress": 96, "message": "正在生成封面动画..."},
        ),
        (
            "log",
            {
                "level": "INFO",
                "logger": "blog_service",
                "message": "开始生成封面动画视频...",
            },
        ),
    ]


def test_single_cover_video_uses_animation_prompt_and_oss_url():
    video_service = MagicMock()
    video_service.is_available.return_value = True
    video_service.generate_from_image.return_value = SimpleNamespace(
        oss_url="https://cdn.example/cover.mp4",
        local_path="/tmp/cover.mp4",
        url="https://provider.example/cover.mp4",
    )

    result = generate_cover_video(
        cover_image_url="https://example.com/cover.png",
        section_images=[],
        get_video_service=MagicMock(return_value=video_service),
        get_oss_service=MagicMock(),
        video_aspect_ratio="9:16",
    )

    assert result == "https://cdn.example/cover.mp4"
    call = video_service.generate_from_image.call_args
    assert call.kwargs["prompt"] == ANIMATION_PROMPT
    assert call.kwargs["aspect_ratio"].value == "9:16"


def test_cover_video_delegates_section_images_to_sequence_function():
    video_service = MagicMock()
    video_service.is_available.return_value = True
    sequence_video = MagicMock(return_value="https://cdn.example/sequence.mp4")

    result = generate_cover_video(
        cover_image_url="cover.png",
        section_images=["one.png", "two.png"],
        get_video_service=MagicMock(return_value=video_service),
        get_oss_service=MagicMock(return_value="oss"),
        generate_sequence_video_fn=sequence_video,
    )

    assert result == "https://cdn.example/sequence.mp4"
    sequence_video.assert_called_once()
    assert sequence_video.call_args.kwargs["video_service"] is video_service
    assert sequence_video.call_args.kwargs["section_images"] == ["one.png", "two.png"]


def test_sequence_video_preserves_segment_order_before_merge():
    video_service = MagicMock()

    def generate_from_image(*, image_url, last_frame_url, **kwargs):
        return SimpleNamespace(oss_url=f"{image_url}->{last_frame_url}", url=None)

    video_service.generate_from_image.side_effect = generate_from_image
    merge = MagicMock(return_value="merged.mp4")

    result = generate_sequence_video(
        cover_image_url="cover",
        section_images=["one", "two"],
        video_service=video_service,
        oss_service="oss",
        merge_videos_fn=merge,
    )

    assert result == "merged.mp4"
    assert merge.call_args.kwargs["video_urls"] == [
        "cover->one",
        "one->two",
    ]


def test_sequence_video_returns_the_only_successful_segment_without_merge():
    video_service = MagicMock()
    video_service.generate_from_image.side_effect = [
        SimpleNamespace(oss_url="segment.mp4", url=None),
        None,
    ]
    merge = MagicMock()

    result = generate_sequence_video(
        cover_image_url="cover",
        section_images=["one", "two"],
        video_service=video_service,
        oss_service="oss",
        merge_videos_fn=merge,
        max_workers=1,
    )

    assert result == "segment.mp4"
    merge.assert_not_called()


def test_merge_videos_command_failure_degrades_to_none(tmp_path):
    class Response:
        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            return [b"video"]

    temporary_directory = MagicMock()
    temporary_directory.return_value.__enter__.return_value = str(tmp_path)
    run_command = MagicMock(return_value=SimpleNamespace(returncode=1, stderr="bad"))

    result = merge_videos(
        video_urls=["https://example.com/one.mp4"],
        oss_service=MagicMock(),
        http_get=MagicMock(return_value=Response()),
        run_command=run_command,
        temporary_directory=temporary_directory,
        uuid_hex=lambda: "12345678",
    )

    assert result is None
    assert run_command.call_args.args[0][0] == "ffmpeg"
