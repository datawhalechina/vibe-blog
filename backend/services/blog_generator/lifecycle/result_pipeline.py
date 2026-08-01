"""Shared post-stream generation result handling."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse


logger = logging.getLogger("services.blog_generator.blog_service")


@dataclass
class GenerationResultRequest:
    task_id: str
    topic: str
    article_type: str
    target_length: str
    final_state: Dict[str, Any]
    article_config: Dict[str, Any]
    generate_images: bool
    generate_cover_video: bool
    video_aspect_ratio: str
    task_manager: Any = None
    token_tracker: Any = None
    task_log: Any = None
    record_memory: bool = False


@dataclass
class GenerationResult:
    markdown: str
    saved_path: Optional[str]
    cover_video_path: Optional[str]
    citations: list


class GenerationResultPipeline:
    def __init__(self, service):
        self.service = service

    def finalize(self, request: GenerationResultRequest) -> GenerationResult:
        final_state = request.final_state
        markdown_content = self.service._validate_final_state(final_state)
        outline = final_state.get("outline") or {}
        cover_image_result = self._generate_cover(request, outline, markdown_content)
        cover_image_url = cover_image_result[0] if cover_image_result else None
        cover_image_path = cover_image_result[1] if cover_image_result else None
        article_summary = (
            cover_image_result[2]
            if cover_image_result and len(cover_image_result) > 2
            else None
        )
        markdown_with_cover = self._insert_cover(
            markdown_content, outline, request.topic, cover_image_path
        )
        saved_path = self.service._save_markdown(
            task_id=request.task_id,
            markdown=markdown_content,
            outline=outline,
            cover_image_path=cover_image_path,
        )
        cover_video_path = self._generate_video(request, cover_image_url)
        citations = self._build_citations(final_state)

        self._persist_and_complete(
            request=request,
            markdown=markdown_with_cover,
            saved_path=saved_path,
            cover_image_path=cover_image_path,
            cover_video_path=cover_video_path,
            article_summary=article_summary,
            citations=citations,
        )
        self._complete_tracking(request)

        return GenerationResult(
            markdown=markdown_with_cover,
            saved_path=saved_path,
            cover_video_path=cover_video_path,
            citations=citations,
        )

    def _generate_cover(self, request, outline, markdown_content):
        if not request.generate_images:
            logger.info("图片生成已禁用，跳过封面图")
            return None
        return self.service._generate_cover_image(
            title=outline.get("title", request.topic),
            topic=request.topic,
            full_content=markdown_content,
            task_manager=request.task_manager,
            task_id=request.task_id,
            image_style=request.final_state.get("image_style", ""),
            video_aspect_ratio=(
                request.video_aspect_ratio if request.generate_cover_video else "16:9"
            ),
        )

    @staticmethod
    def _insert_cover(markdown, outline, topic, cover_image_path):
        if not cover_image_path or not markdown:
            return markdown
        title = outline.get("title", topic)
        if cover_image_path.startswith("http"):
            cover_image_ref = cover_image_path
        else:
            cover_image_ref = f"./images/{os.path.basename(cover_image_path)}"
        cover_section = f"\n![{title} - 架构图]({cover_image_ref})\n\n---\n\n"
        lines = markdown.split("\n")
        insert_idx = 0
        for index, line in enumerate(lines):
            if line.startswith("## ") and index > 0:
                insert_idx = index
                break
        if insert_idx > 0:
            lines.insert(insert_idx, cover_section)
            return "\n".join(lines)
        return cover_section + markdown

    def _generate_video(self, request, cover_image_url):
        enabled = os.environ.get("COVER_VIDEO_ENABLED", "true").lower() == "true"
        if not (request.generate_cover_video and cover_image_url and enabled):
            return None
        return self.service._generate_cover_video(
            history_id=request.task_id,
            cover_image_url=cover_image_url,
            video_aspect_ratio=request.video_aspect_ratio,
            task_manager=request.task_manager,
            task_id=request.task_id,
            section_images=request.final_state.get("section_images", []),
        )

    @staticmethod
    def _build_citations(final_state):
        citations = []
        seen_urls = set()
        for source_key in ("search_results", "top_references"):
            for reference in final_state.get(source_key) or []:
                url = reference.get("url") or reference.get("source", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                try:
                    domain = urlparse(url).hostname or ""
                except Exception:
                    domain = ""
                citations.append(
                    {
                        "url": url,
                        "title": reference.get("title", ""),
                        "domain": domain,
                        "snippet": (
                            reference.get("content", "")
                            or reference.get("snippet", "")
                        )[:80],
                    }
                )
        return citations

    def _persist_and_complete(
        self,
        *,
        request,
        markdown,
        saved_path,
        cover_image_path,
        cover_video_path,
        article_summary,
        citations,
    ):
        try:
            from services.database_service import get_db_service

            db_service = get_db_service()
            final_state = request.final_state
            article_config = request.article_config
            db_service.save_history(
                history_id=request.task_id,
                topic=request.topic,
                article_type=request.article_type,
                target_length=request.target_length,
                markdown_content=markdown,
                outline=json.dumps(final_state.get("outline") or {}, ensure_ascii=False),
                sections_count=len(final_state.get("sections", [])),
                code_blocks_count=len(final_state.get("code_blocks", [])),
                images_count=len(final_state.get("images", [])),
                review_score=final_state.get("review_score", 0),
                cover_image=cover_image_path,
                cover_video=cover_video_path,
                target_sections_count=article_config.get("sections_count"),
                target_images_count=article_config.get("images_count"),
                target_code_blocks_count=article_config.get("code_blocks_count"),
                target_word_count=article_config.get("target_word_count"),
                citations=json.dumps(citations, ensure_ascii=False) if citations else None,
            )
            logger.info(f"历史记录已保存: {request.task_id}")
            self.service._send_completion_event(
                task_manager=request.task_manager,
                task_id=request.task_id,
                final_state=final_state,
                markdown=markdown,
                saved_path=saved_path,
                cover_video_path=cover_video_path,
                citations=citations,
            )
            self._record_memory(request)
            self._save_summary(request, db_service, markdown, article_summary)
        except Exception as error:
            logger.warning(f"保存历史记录失败: {error}")
            raise RuntimeError(f"保存历史记录失败: {error}") from error

    def _record_memory(self, request):
        storage = getattr(self.service.generator, "_memory_storage", None)
        if not request.record_memory or not storage:
            return
        try:
            storage.add_fact(
                "default",
                f"生成了关于 {request.topic} 的 {request.article_type} 文章",
                category="behavior",
                confidence=0.8,
                source=f"task:{request.task_id}",
            )
        except Exception as error:
            logger.debug(f"记忆记录跳过: {error}")

    def _save_summary(self, request, db_service, markdown, article_summary):
        try:
            summary = article_summary
            if not summary:
                from services.blog_generator import blog_service

                summary = blog_service.extract_article_summary(
                    llm_client=self.service.generator.llm,
                    title=request.topic,
                    content=markdown,
                    max_length=500,
                )
            if summary:
                db_service.update_history_summary(request.task_id, summary[:500])
                if request.record_memory:
                    logger.info(f"博客摘要已保存: {request.task_id}")
        except Exception as error:
            logger.warning(f"保存博客摘要失败: {error}")

    @staticmethod
    def _complete_tracking(request):
        token_summary = None
        if request.token_tracker:
            try:
                logger.info(request.token_tracker.format_summary())
                token_summary = request.token_tracker.get_summary()
            except Exception as error:
                logger.warning(f"Token 摘要生成失败: {error}")
        if request.task_log:
            try:
                final_state = request.final_state
                request.task_log.complete(
                    score=final_state.get("review_score", 0),
                    word_count=len(final_state.get("final_markdown", "")),
                    revision_rounds=final_state.get("revision_count", 0),
                )
                if token_summary:
                    request.task_log.token_summary = token_summary
                request.task_log.save()
                logger.info(request.task_log.get_summary())
            except Exception as error:
                logger.warning(f"任务日志保存失败: {error}")
