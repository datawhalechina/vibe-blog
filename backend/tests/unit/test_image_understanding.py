"""
图片理解服务 + 视觉中间件 单元测试

测试 ImageUnderstandingService 的图片读取、base64 编码、分析功能，
以及 VisionMiddleware 的节点级注入逻辑。
"""
import base64
import os
import pytest
from unittest.mock import MagicMock, patch

from services.image_understanding_service import (
    ImageUnderstandingService,
    ViewedImage,
    ImageUnderstanding,
    VALID_IMAGE_EXTENSIONS,
)


# ==================== ImageUnderstandingService Tests ====================


class TestReadImage:
    """图片读取与 base64 编码测试"""

    def test_read_valid_png(self, tmp_path):
        """读取合法 PNG 文件应返回 ViewedImage"""
        img_file = tmp_path / "test.png"
        raw = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        img_file.write_bytes(raw)

        svc = ImageUnderstandingService()
        result = svc.read_image(str(img_file))

        assert result is not None
        assert result.mime_type == "image/png"
        assert len(result.base64) > 0
        assert base64.b64decode(result.base64) == raw

    def test_read_valid_jpeg(self, tmp_path):
        """读取合法 JPEG 文件"""
        img_file = tmp_path / "photo.jpg"
        raw = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        img_file.write_bytes(raw)

        svc = ImageUnderstandingService()
        result = svc.read_image(str(img_file))

        assert result is not None
        assert result.mime_type == "image/jpeg"

    def test_read_valid_webp(self, tmp_path):
        """读取合法 WebP 文件"""
        img_file = tmp_path / "image.webp"
        img_file.write_bytes(b"RIFF" + b"\x00" * 100)

        svc = ImageUnderstandingService()
        result = svc.read_image(str(img_file))

        assert result is not None
        assert result.mime_type == "image/webp"

    def test_read_valid_gif(self, tmp_path):
        """读取合法 GIF 文件"""
        img_file = tmp_path / "anim.gif"
        img_file.write_bytes(b"GIF89a" + b"\x00" * 100)

        svc = ImageUnderstandingService()
        result = svc.read_image(str(img_file))

        assert result is not None
        assert result.mime_type == "image/gif"

    def test_read_nonexistent_file(self):
        """不存在的文件应返回 None"""
        svc = ImageUnderstandingService()
        result = svc.read_image("/tmp/nonexistent_image_12345.png")
        assert result is None

    def test_read_unsupported_format(self, tmp_path):
        """不支持的格式（.bmp）应返回 None"""
        bmp_file = tmp_path / "test.bmp"
        bmp_file.write_bytes(b"BM" + b"\x00" * 100)

        svc = ImageUnderstandingService()
        result = svc.read_image(str(bmp_file))
        assert result is None

    def test_read_relative_path(self):
        """相对路径应返回 None"""
        svc = ImageUnderstandingService()
        result = svc.read_image("relative/path/image.png")
        assert result is None

    def test_read_directory_not_file(self, tmp_path):
        """目录路径应返回 None"""
        svc = ImageUnderstandingService()
        result = svc.read_image(str(tmp_path))
        assert result is None

    def test_viewed_images_state(self, tmp_path):
        """读取后应记录到 viewed_images 状态"""
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        svc = ImageUnderstandingService()
        svc.read_image(str(img_file))

        viewed = svc.get_viewed_images()
        assert str(img_file) in viewed
        assert viewed[str(img_file)].mime_type == "image/jpeg"

    def test_clear_viewed_images(self, tmp_path):
        """clear 应清空所有已查看图片"""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        svc = ImageUnderstandingService()
        svc.read_image(str(img_file))
        assert len(svc.get_viewed_images()) == 1

        svc.clear_viewed_images()
        assert len(svc.get_viewed_images()) == 0

    def test_multiple_images(self, tmp_path):
        """读取多张图片应全部记录"""
        for name in ["a.png", "b.jpg", "c.webp"]:
            (tmp_path / name).write_bytes(b"\x00" * 50)

        svc = ImageUnderstandingService()
        for name in ["a.png", "b.jpg", "c.webp"]:
            svc.read_image(str(tmp_path / name))

        assert len(svc.get_viewed_images()) == 3

    def test_valid_extensions_set(self):
        """验证支持的扩展名集合"""
        assert ".jpg" in VALID_IMAGE_EXTENSIONS
        assert ".jpeg" in VALID_IMAGE_EXTENSIONS
        assert ".png" in VALID_IMAGE_EXTENSIONS
        assert ".webp" in VALID_IMAGE_EXTENSIONS
        assert ".gif" in VALID_IMAGE_EXTENSIONS
        assert ".bmp" not in VALID_IMAGE_EXTENSIONS


class TestAnalyzeImage:
    """图片分析测试"""

    def test_analyze_with_mock_llm(self, tmp_path):
        """使用 mock LLM 测试图片分析"""
        img_file = tmp_path / "diagram.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        mock_llm = MagicMock()
        mock_llm.chat_with_image.return_value = (
            '{"description": "架构图", "detected_text": null, '
            '"image_type": "diagram", "relevance_score": 0.8}'
        )

        svc = ImageUnderstandingService(llm_service=mock_llm)
        result = svc.analyze_image(str(img_file), context="系统架构设计")

        assert result is not None
        assert result.image_type == "diagram"
        assert result.relevance_score == 0.8
        assert result.description == "架构图"
        mock_llm.chat_with_image.assert_called_once()

    def test_analyze_with_code_fence_response(self, tmp_path):
        """LLM 返回带 code fence 的 JSON 应正确解析"""
        img_file = tmp_path / "chart.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        mock_llm = MagicMock()
        mock_llm.chat_with_image.return_value = (
            '```json\n{"description": "数据图表", "detected_text": "2024 Q1",'
            ' "image_type": "chart", "relevance_score": 0.9}\n```'
        )

        svc = ImageUnderstandingService(llm_service=mock_llm)
        result = svc.analyze_image(str(img_file))

        assert result is not None
        assert result.image_type == "chart"
        assert result.detected_text == "2024 Q1"

    def test_analyze_with_invalid_json_response(self, tmp_path):
        """LLM 返回非 JSON 应 fallback"""
        img_file = tmp_path / "photo.jpg"
        img_file.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        mock_llm = MagicMock()
        mock_llm.chat_with_image.return_value = "这是一张风景照片"

        svc = ImageUnderstandingService(llm_service=mock_llm)
        result = svc.analyze_image(str(img_file))

        assert result is not None
        assert result.image_type == "other"
        assert result.relevance_score == 0.5
        assert "风景照片" in result.description

    def test_analyze_without_llm(self, tmp_path):
        """无 LLM 服务时应返回 None"""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        svc = ImageUnderstandingService(llm_service=None)
        result = svc.analyze_image(str(img_file))
        assert result is None

    def test_analyze_nonexistent_file(self):
        """分析不存在的文件应返回 None"""
        mock_llm = MagicMock()
        svc = ImageUnderstandingService(llm_service=mock_llm)
        result = svc.analyze_image("/tmp/no_such_file_99999.png")
        assert result is None
        mock_llm.chat_with_image.assert_not_called()

    def test_analyze_reuses_cached_image(self, tmp_path):
        """分析已读取的图片应复用缓存，不重复读取"""
        img_file = tmp_path / "cached.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        mock_llm = MagicMock()
        mock_llm.chat_with_image.return_value = '{"description": "test", "image_type": "other", "relevance_score": 0.5}'

        svc = ImageUnderstandingService(llm_service=mock_llm)
        svc.read_image(str(img_file))

        # 删除文件后仍能分析（因为已缓存）
        img_file.unlink()
        result = svc.analyze_image(str(img_file))
        assert result is not None

    def test_analyze_llm_returns_none(self, tmp_path):
        """LLM 返回 None 时应返回 None"""
        img_file = tmp_path / "fail.png"
        img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        mock_llm = MagicMock()
        mock_llm.chat_with_image.return_value = None

        svc = ImageUnderstandingService(llm_service=mock_llm)
        result = svc.analyze_image(str(img_file))
        assert result is None


# ==================== VisionMiddleware Tests ====================


class TestVisionMiddleware:
    """VisionMiddleware 节点级注入测试"""

    def test_skip_when_disabled(self):
        """VISION_ENABLED=false 时应跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mw = VisionMiddleware()
        with patch.dict(os.environ, {"VISION_ENABLED": "false"}):
            result = mw.before_node({"viewed_images": {"/a.png": {}}}, "writer")
        assert result is None

    def test_skip_when_env_not_set(self):
        """VISION_ENABLED 未设置时默认跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mw = VisionMiddleware()
        env = os.environ.copy()
        env.pop("VISION_ENABLED", None)
        with patch.dict(os.environ, env, clear=True):
            result = mw.before_node({"viewed_images": {"/a.png": {}}}, "writer")
        assert result is None

    def test_skip_non_target_node(self):
        """非目标节点应跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mw = VisionMiddleware()
        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node({"viewed_images": {"/a.png": {}}}, "researcher")
        assert result is None

    def test_skip_empty_viewed_images(self):
        """无图片时应跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mw = VisionMiddleware()
        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node({"viewed_images": {}}, "writer")
        assert result is None

    def test_skip_already_analyzed(self):
        """已有理解结果时应跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mw = VisionMiddleware()
        state = {
            "viewed_images": {"/a.png": {}},
            "image_understandings": [{"path": "/a.png"}],
        }
        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node(state, "writer")
        assert result is None

    def test_skip_no_image_service(self):
        """无 image_service 时应跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mw = VisionMiddleware(image_service=None)
        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node({"viewed_images": {"/a.png": {}}}, "writer")
        assert result is None

    def test_inject_understandings(self):
        """目标节点应注入图片理解结果"""
        from services.blog_generator.middleware import VisionMiddleware

        mock_svc = MagicMock()
        mock_svc.analyze_image.return_value = ImageUnderstanding(
            path="/tmp/a.png",
            description="测试图片",
            detected_text=None,
            image_type="photo",
            relevance_score=0.7,
        )

        mw = VisionMiddleware(image_service=mock_svc)
        state = {"viewed_images": {"/tmp/a.png": {}}, "topic": "测试"}

        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node(state, "writer")

        assert result is not None
        assert len(result["image_understandings"]) == 1
        assert result["image_understandings"][0]["image_type"] == "photo"
        assert result["image_understandings"][0]["relevance_score"] == 0.7

    def test_inject_multiple_images(self):
        """多张图片应全部注入"""
        from services.blog_generator.middleware import VisionMiddleware

        mock_svc = MagicMock()
        mock_svc.analyze_image.side_effect = [
            ImageUnderstanding("/a.png", "图A", None, "diagram", 0.8),
            ImageUnderstanding("/b.jpg", "图B", "text", "screenshot", 0.6),
        ]

        mw = VisionMiddleware(image_service=mock_svc)
        state = {
            "viewed_images": {"/a.png": {}, "/b.jpg": {}},
            "topic": "test",
        }

        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node(state, "planner")

        assert result is not None
        assert len(result["image_understandings"]) == 2

    def test_analyze_failure_skipped(self):
        """分析失败的图片应被跳过"""
        from services.blog_generator.middleware import VisionMiddleware

        mock_svc = MagicMock()
        mock_svc.analyze_image.return_value = None

        mw = VisionMiddleware(image_service=mock_svc)
        state = {"viewed_images": {"/fail.png": {}}, "topic": "test"}

        with patch.dict(os.environ, {"VISION_ENABLED": "true"}):
            result = mw.before_node(state, "writer")

        assert result is None

    def test_target_nodes(self):
        """验证所有目标节点都能触发注入"""
        from services.blog_generator.middleware import VisionMiddleware, VISION_ENABLED_NODES

        assert "planner" in VISION_ENABLED_NODES
        assert "writer" in VISION_ENABLED_NODES
        assert "artist" in VISION_ENABLED_NODES
        assert "assembler" in VISION_ENABLED_NODES
