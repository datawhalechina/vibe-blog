"""
markitdown 文档转换测试 — TDD Red Phase

测试 FileParserService 的 markitdown 快速转换通道：
- Office 文档 (PPT/PPTX/XLS/XLSX/DOC/DOCX) 优先使用 markitdown
- markitdown 失败时回退到 MinerU
- 扩展后的文件类型白名单
"""
import sys
import pytest
from unittest.mock import patch, MagicMock


class TestMarkitdownConversion:
    """markitdown 快速转换通道测试"""

    def setup_method(self):
        from services.file_parser_service import FileParserService
        self.parser = FileParserService(
            mineru_token="test_token",
            upload_folder="/tmp/test_uploads"
        )

    @patch('markitdown.MarkItDown')
    def test_pptx_converts_successfully(self, mock_md_cls):
        """PPT 文件应通过 markitdown 成功转换"""
        mock_result = MagicMock()
        mock_result.text_content = "# Slide 1\n\nContent here"
        mock_md_cls.return_value.convert.return_value = mock_result

        result = self.parser._parse_with_markitdown("/tmp/test.pptx", "test.pptx")
        assert result['success'] is True
        assert "Slide 1" in result['markdown']
        assert result['images'] == []

    @patch('markitdown.MarkItDown')
    def test_docx_converts_successfully(self, mock_md_cls):
        """DOCX 文件应通过 markitdown 成功转换"""
        mock_result = MagicMock()
        mock_result.text_content = "# Document Title\n\nParagraph content"
        mock_md_cls.return_value.convert.return_value = mock_result

        result = self.parser._parse_with_markitdown("/tmp/test.docx", "test.docx")
        assert result['success'] is True
        assert "Document Title" in result['markdown']

    @patch('markitdown.MarkItDown')
    def test_xlsx_converts_successfully(self, mock_md_cls):
        """XLSX 文件应通过 markitdown 成功转换"""
        mock_result = MagicMock()
        mock_result.text_content = "| Col1 | Col2 |\n|---|---|\n| A | B |"
        mock_md_cls.return_value.convert.return_value = mock_result

        result = self.parser._parse_with_markitdown("/tmp/test.xlsx", "test.xlsx")
        assert result['success'] is True
        assert "Col1" in result['markdown']

    @patch('markitdown.MarkItDown')
    def test_empty_result_returns_failure(self, mock_md_cls):
        """转换结果为空时应返回失败"""
        mock_result = MagicMock()
        mock_result.text_content = ""
        mock_md_cls.return_value.convert.return_value = mock_result

        result = self.parser._parse_with_markitdown("/tmp/test.docx", "test.docx")
        assert result['success'] is False
        assert 'markitdown 转换结果为空' in result['error']

    @patch('markitdown.MarkItDown')
    def test_whitespace_only_result_returns_failure(self, mock_md_cls):
        """转换结果仅含空白时应返回失败"""
        mock_result = MagicMock()
        mock_result.text_content = "   \n\n  "
        mock_md_cls.return_value.convert.return_value = mock_result

        result = self.parser._parse_with_markitdown("/tmp/test.pptx", "test.pptx")
        assert result['success'] is False

    @patch('markitdown.MarkItDown')
    def test_conversion_exception_returns_none(self, mock_md_cls):
        """markitdown 转换异常时应返回 None（触发回退）"""
        mock_md_cls.return_value.convert.side_effect = RuntimeError("conversion failed")

        result = self.parser._parse_with_markitdown("/tmp/test.docx", "test.docx")
        assert result is None


class TestParseFileRouting:
    """parse_file 路由逻辑测试"""

    def setup_method(self):
        from services.file_parser_service import FileParserService
        self.parser = FileParserService(
            mineru_token="test_token",
            upload_folder="/tmp/test_uploads"
        )

    def test_parse_file_routes_office_to_markitdown(self):
        """parse_file 应将 Office 文档路由到 markitdown"""
        with patch.object(self.parser, '_parse_with_markitdown') as mock_mk:
            mock_mk.return_value = {
                'success': True, 'markdown': '# Test', 'images': [],
                'batch_id': None, 'mineru_folder': None, 'error': None
            }
            result = self.parser.parse_file("/tmp/test.docx", "test.docx")
            mock_mk.assert_called_once()
            assert result['success'] is True

    def test_parse_file_routes_pptx_to_markitdown(self):
        """parse_file 应将 PPTX 路由到 markitdown"""
        with patch.object(self.parser, '_parse_with_markitdown') as mock_mk:
            mock_mk.return_value = {
                'success': True, 'markdown': '# Slides', 'images': [],
                'batch_id': None, 'mineru_folder': None, 'error': None
            }
            result = self.parser.parse_file("/tmp/test.pptx", "test.pptx")
            mock_mk.assert_called_once()

    def test_parse_file_routes_xlsx_to_markitdown(self):
        """parse_file 应将 XLSX 路由到 markitdown"""
        with patch.object(self.parser, '_parse_with_markitdown') as mock_mk:
            mock_mk.return_value = {
                'success': True, 'markdown': '| A |', 'images': [],
                'batch_id': None, 'mineru_folder': None, 'error': None
            }
            result = self.parser.parse_file("/tmp/test.xlsx", "test.xlsx")
            mock_mk.assert_called_once()

    def test_parse_file_fallback_to_mineru_on_failure(self):
        """markitdown 失败时应回退到 MinerU"""
        with patch.object(self.parser, '_parse_with_markitdown', return_value=None), \
             patch.object(self.parser, '_parse_with_mineru') as mock_mineru:
            mock_mineru.return_value = {
                'success': True, 'markdown': '# MinerU Result',
                'images': [], 'batch_id': 'b1',
                'mineru_folder': '/tmp/m', 'error': None
            }
            result = self.parser.parse_file("/tmp/test.pptx", "test.pptx")
            mock_mineru.assert_called_once()

    def test_parse_file_fallback_on_unsuccessful_markitdown(self):
        """markitdown 返回 success=False 时也应回退到 MinerU"""
        with patch.object(self.parser, '_parse_with_markitdown') as mock_mk, \
             patch.object(self.parser, '_parse_with_mineru') as mock_mineru:
            mock_mk.return_value = {
                'success': False, 'markdown': None, 'images': None,
                'batch_id': None, 'mineru_folder': None,
                'error': 'markitdown 转换结果为空'
            }
            mock_mineru.return_value = {
                'success': True, 'markdown': '# Fallback',
                'images': [], 'batch_id': 'b2',
                'mineru_folder': '/tmp/m2', 'error': None
            }
            result = self.parser.parse_file("/tmp/test.docx", "test.docx")
            mock_mineru.assert_called_once()

    def test_pdf_still_goes_to_mineru(self):
        """PDF 文件不应走 markitdown，仍走 MinerU"""
        with patch.object(self.parser, '_parse_with_markitdown') as mock_mk, \
             patch.object(self.parser, '_get_pdf_page_count', return_value=5), \
             patch.object(self.parser, '_parse_with_mineru') as mock_mineru:
            mock_mineru.return_value = {
                'success': True, 'markdown': '# PDF', 'images': [],
                'batch_id': 'b3', 'mineru_folder': '/tmp/m3', 'error': None
            }
            result = self.parser.parse_file("/tmp/test.pdf", "test.pdf")
            mock_mk.assert_not_called()
            mock_mineru.assert_called_once()

    def test_txt_still_reads_directly(self):
        """TXT 文件仍应直接读取"""
        with patch.object(self.parser, '_parse_with_markitdown') as mock_mk, \
             patch.object(self.parser, '_parse_text_file') as mock_txt:
            mock_txt.return_value = {
                'success': True, 'markdown': 'plain text',
                'images': [], 'batch_id': None,
                'mineru_folder': None, 'error': None
            }
            result = self.parser.parse_file("/tmp/test.txt", "test.txt")
            mock_mk.assert_not_called()
            mock_txt.assert_called_once()


class TestAllowedExtensions:
    """上传路由文件类型白名单测试"""

    def test_allowed_extensions_includes_office_formats(self):
        """验证扩展后的文件类型白名单包含 Office 格式"""
        from routes.blog_routes import ALLOWED_EXTENSIONS
        expected = {'pdf', 'md', 'txt', 'markdown', 'ppt', 'pptx',
                    'xls', 'xlsx', 'doc', 'docx'}
        assert ALLOWED_EXTENSIONS == expected

    def test_markitdown_extensions_constant(self):
        """验证 MARKITDOWN_EXTENSIONS 常量"""
        from services.file_parser_service import MARKITDOWN_EXTENSIONS
        expected = {'ppt', 'pptx', 'xls', 'xlsx', 'doc', 'docx'}
        assert MARKITDOWN_EXTENSIONS == expected
