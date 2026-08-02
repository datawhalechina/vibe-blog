"""Media generation functions used by the generation result lifecycle."""

import logging
import os
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

import requests

from services.media import AspectRatio, ImageSize, VideoAspectRatio


logger = logging.getLogger("services.blog_generator.blog_service")

ANIMATION_PROMPT = """Add subtle animations to non-text elements only:
- Gears: rotate slowly (max 5 degrees/sec)
- Arrows: gentle glow pulse
- Icons: slight floating effect

CRITICAL: ALL TEXT (Chinese characters, English, numbers) MUST remain completely static.
Do NOT animate, move, scale, blur, or distort any text.
Text areas are NO-ANIMATION zones.

Duration: 6-8 seconds. Professional educational style."""


def _emit(emit_event, event_name: str, payload: dict) -> None:
    if emit_event:
        emit_event(event_name, payload)


def generate_cover_image(
    *,
    title: str,
    topic: str,
    full_content: str,
    llm_client,
    image_service,
    summarize: Callable,
    render_style_prompt: Callable,
    render_default_prompt: Callable,
    emit_event: Optional[Callable] = None,
    image_style: str = "",
    video_aspect_ratio: str = "16:9",
) -> Optional[tuple]:
    """Generate a cover image while preserving the existing degradation contract."""
    if not image_service or not image_service.is_available():
        logger.warning("图片生成服务不可用，跳过封面图生成")
        return None

    try:
        _emit(emit_event, "log", {
            "level": "INFO",
            "logger": "blog_service",
            "message": "正在提炼文章摘要...",
        })
        article_summary = summarize(
            llm_client=llm_client,
            title=title,
            content=full_content,
            max_length=None,
        )
        if not article_summary:
            article_summary = f"标题：{title}\n主题：{topic}"

        _emit(emit_event, "log", {
            "level": "INFO",
            "logger": "blog_service",
            "message": "正在生成封面架构图...",
        })
        if image_style:
            cover_prompt = render_style_prompt(image_style, article_summary)
            logger.info(f"开始生成【封面图】({image_style}): {title}")
        else:
            cover_prompt = render_default_prompt(article_summary)
            logger.info(f"开始生成【封面图】: {title}")

        image_aspect_ratio = (
            AspectRatio.PORTRAIT_9_16
            if video_aspect_ratio == "9:16"
            else AspectRatio.LANDSCAPE_16_9
        )
        logger.info(
            "封面图参数: video_aspect_ratio=%s, image_aspect_ratio=%s",
            video_aspect_ratio,
            image_aspect_ratio.value,
        )
        result = image_service.generate(
            prompt=cover_prompt,
            aspect_ratio=image_aspect_ratio,
            image_size=ImageSize.SIZE_2K,
            download=True,
        )
        if result and (result.oss_url or result.local_path):
            final_url = result.oss_url or result.url
            final_path = result.oss_url or result.local_path
            logger.info(f"封面图生成成功: {final_url}")
            _emit(emit_event, "log", {
                "level": "INFO",
                "logger": "blog_service",
                "message": "封面架构图生成完成",
            })
            return final_url, final_path, article_summary

        logger.warning("封面图生成失败，未获取到图片路径")
        return None, None, article_summary
    except Exception as error:
        logger.error(f"封面图生成失败: {error}")
        return None


def merge_videos(
    *,
    video_urls: list,
    oss_service,
    http_get: Callable = requests.get,
    run_command: Callable = subprocess.run,
    temporary_directory: Callable = tempfile.TemporaryDirectory,
    uuid_hex: Callable = lambda: uuid.uuid4().hex[:8],
) -> Optional[str]:
    """Download, concatenate, and upload video segments."""
    try:
        with temporary_directory() as temp_dir:
            local_videos = []
            for index, url in enumerate(video_urls):
                local_path = os.path.join(temp_dir, f"segment_{index}.mp4")
                logger.info(f"下载视频片段 {index + 1}: {url[:80]}...")
                response = http_get(url, timeout=120, stream=True)
                response.raise_for_status()
                with open(local_path, "wb") as output:
                    for chunk in response.iter_content(chunk_size=8192):
                        output.write(chunk)
                local_videos.append(local_path)
                logger.info(f"视频片段 {index + 1} 下载完成")

            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as output:
                for video_path in local_videos:
                    output.write(f"file '{video_path}'\n")

            output_path = os.path.join(temp_dir, f"merged_{uuid_hex()}.mp4")
            command = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", output_path,
            ]
            logger.info(f"执行 FFmpeg 合并: {' '.join(command)}")
            result = run_command(
                command,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(f"FFmpeg 合并失败: {result.stderr}")
                return None

            if oss_service and os.path.exists(output_path):
                oss_url = oss_service.upload_file(
                    output_path,
                    f"videos/merged_{uuid_hex()}.mp4",
                )
                if oss_url:
                    logger.info(f"合并视频已上传到 OSS: {oss_url}")
                    return oss_url
            return output_path
    except Exception as error:
        logger.error(f"视频合并失败: {error}", exc_info=True)
        return None


def generate_sequence_video(
    *,
    cover_image_url: str,
    section_images: list,
    video_service,
    oss_service,
    emit_event: Optional[Callable] = None,
    video_aspect_ratio: str = "16:9",
    merge_videos_fn: Callable = merge_videos,
    max_workers: int = 2,
) -> Optional[str]:
    """Generate ordered transitions and merge the successful segments."""
    all_images = [cover_image_url] + section_images
    segment_count = len(all_images) - 1
    logger.info(
        f"开始生成混合序列视频: {len(all_images)} 张图片 → {segment_count} 个 Veo3 动画"
    )
    _emit(emit_event, "log", {
        "level": "INFO",
        "logger": "blog_service",
        "message": f"开始生成混合序列视频: {len(all_images)} 张图片",
    })
    aspect_ratio = (
        VideoAspectRatio.PORTRAIT_9_16
        if video_aspect_ratio == "9:16"
        else VideoAspectRatio.LANDSCAPE_16_9
    )

    def generate_segment(index: int, first_frame: str, last_frame: str):
        try:
            logger.info(
                f"[并行] 生成 Veo3 动画视频 {index + 1}: "
                f"{first_frame[:50]}... → {last_frame[:50]}..."
            )
            result = video_service.generate_from_image(
                image_url=first_frame,
                prompt=ANIMATION_PROMPT,
                aspect_ratio=aspect_ratio,
                last_frame_url=last_frame,
            )
            if result and (result.oss_url or result.url):
                logger.info(f"✅ Veo3 动画视频 {index + 1} 生成成功")
                return {"idx": index, "url": result.oss_url or result.url}
            logger.warning(f"⚠️ Veo3 动画视频 {index + 1} 生成失败")
        except Exception as error:
            logger.warning(f"⚠️ Veo3 动画视频 {index + 1} 生成异常: {error}")
        return {"idx": index, "url": None}

    _emit(emit_event, "log", {
        "level": "INFO",
        "logger": "blog_service",
        "message": f"开始并行生成视频（最大并行数 {max_workers}）...",
    })
    results = [None] * segment_count
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(generate_segment, index, all_images[index], all_images[index + 1])
            for index in range(segment_count)
        ]
        for future in as_completed(futures):
            result = future.result()
            results[result["idx"]] = result["url"]

    video_urls = [url for url in results if url]
    if not video_urls:
        logger.error("没有成功生成的视频片段")
        return None
    logger.info(f"成功生成 {len(video_urls)} 个视频片段，开始合并...")
    _emit(emit_event, "log", {
        "level": "INFO",
        "logger": "blog_service",
        "message": f"成功生成 {len(video_urls)} 个片段，开始合并...",
    })
    if len(video_urls) == 1:
        return video_urls[0]

    final_video_url = merge_videos_fn(
        video_urls=video_urls,
        oss_service=oss_service,
    )
    if final_video_url:
        logger.info(f"序列视频合并成功: {final_video_url}")
        _emit(emit_event, "log", {
            "level": "INFO",
            "logger": "blog_service",
            "message": f"序列视频生成完成: {len(video_urls)} 个片段已合并",
        })
    return final_video_url


def generate_cover_video(
    *,
    cover_image_url: str,
    section_images: list,
    get_video_service: Callable,
    get_oss_service: Callable,
    emit_event: Optional[Callable] = None,
    video_aspect_ratio: str = "16:9",
    generate_sequence_video_fn: Callable = generate_sequence_video,
) -> Optional[str]:
    """Generate a single-image animation or a multi-image sequence."""
    try:
        _emit(emit_event, "progress", {
            "stage": "video",
            "progress": 96,
            "message": "正在生成封面动画...",
        })
        _emit(emit_event, "log", {
            "level": "INFO",
            "logger": "blog_service",
            "message": "开始生成封面动画视频...",
        })
        video_service = get_video_service()
        if not video_service or not video_service.is_available():
            logger.warning("视频生成服务不可用，跳过封面动画生成")
            return None
        oss_service = get_oss_service()

        if section_images:
            logger.info(f"使用多图序列模式: 封面图 + {len(section_images)} 张章节配图")
            return generate_sequence_video_fn(
                cover_image_url=cover_image_url,
                section_images=section_images,
                video_service=video_service,
                oss_service=oss_service,
                emit_event=emit_event,
                video_aspect_ratio=video_aspect_ratio,
            )

        logger.info(f"使用单图模式: {cover_image_url}")
        aspect_ratio = (
            VideoAspectRatio.PORTRAIT_9_16
            if video_aspect_ratio == "9:16"
            else VideoAspectRatio.LANDSCAPE_16_9
        )

        def progress_callback(progress, status):
            _emit(emit_event, "log", {
                "level": "INFO",
                "logger": "blog_service",
                "message": f"视频生成进度: {progress}%",
            })

        result = video_service.generate_from_image(
            image_url=cover_image_url,
            prompt=ANIMATION_PROMPT,
            aspect_ratio=aspect_ratio,
            progress_callback=progress_callback,
        )
        if not result:
            logger.warning("视频生成失败")
            return None
        if result.oss_url:
            video_access_url = result.oss_url
        elif result.local_path:
            video_access_url = f"/outputs/videos/{os.path.basename(result.local_path)}"
        else:
            video_access_url = result.url
        logger.info(f"封面动画生成成功: {video_access_url}")
        _emit(emit_event, "log", {
            "level": "INFO",
            "logger": "blog_service",
            "message": "封面动画生成完成",
        })
        return video_access_url
    except Exception as error:
        logger.error(f"封面动画生成失败: {error}", exc_info=True)
        return None
