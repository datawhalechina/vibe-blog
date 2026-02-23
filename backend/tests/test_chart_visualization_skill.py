"""
图表可视化 Skill — 单元测试

TDD Red: 先写测试，再实现 chart_visualization skill。
运行: cd backend && python -m pytest tests/test_chart_visualization_skill.py -v
"""
import pytest
from unittest.mock import patch, MagicMock

from services.blog_generator.skills.chart_visualization import (
    extract_chart_blocks,
    replace_chart_blocks_with_images,
    chart_visualization_skill,
)


# ==================== extract_chart_blocks ====================

class TestExtractChartBlocks:

    def test_extract_single_block(self):
        md = '# Title\n```chart\n{"type": "pie", "data": [{"category": "A", "value": 1}]}\n```\ntext'
        blocks = extract_chart_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "pie"
        assert len(blocks[0]["data"]) == 1

    def test_extract_multiple_blocks(self):
        md = (
            '```chart\n{"type": "pie", "data": [{"c": "A", "v": 1}]}\n```\n'
            'Some text\n'
            '```chart\n{"type": "line", "data": [{"x": 1, "y": 2}]}\n```'
        )
        blocks = extract_chart_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "pie"
        assert blocks[1]["type"] == "line"

    def test_no_chart_blocks(self):
        md = "# Title\nJust text\n```python\nprint('hi')\n```"
        assert extract_chart_blocks(md) == []

    def test_invalid_json_skipped(self):
        md = '```chart\n{invalid json}\n```'
        assert extract_chart_blocks(md) == []

    def test_missing_type_skipped(self):
        md = '```chart\n{"data": [1, 2, 3]}\n```'
        assert extract_chart_blocks(md) == []

    def test_missing_data_skipped(self):
        md = '```chart\n{"type": "pie"}\n```'
        assert extract_chart_blocks(md) == []

    def test_multiline_json(self):
        md = '```chart\n{\n  "type": "bar",\n  "data": [{"x": "A", "y": 10}]\n}\n```'
        blocks = extract_chart_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "bar"

    def test_empty_string(self):
        assert extract_chart_blocks("") == []


# ==================== replace_chart_blocks_with_images ====================

class TestReplaceChartBlocks:

    def test_successful_replacement(self):
        md = 'Before\n```chart\n{"type":"pie","data":[]}\n```\nAfter'
        results = [{"success": True, "url": "https://img.example.com/pie.png", "type": "pie"}]
        new_md = replace_chart_blocks_with_images(md, results)
        assert "![pie](https://img.example.com/pie.png)" in new_md
        assert "```chart" not in new_md
        assert "Before" in new_md
        assert "After" in new_md

    def test_failed_chart_preserved(self):
        md = '```chart\n{"type":"line","data":[]}\n```'
        results = [{"success": False, "error": "timeout", "type": "line"}]
        new_md = replace_chart_blocks_with_images(md, results)
        assert "图表生成失败" in new_md
        assert "```chart" in new_md

    def test_multiple_replacements(self):
        md = (
            '```chart\n{"type":"pie","data":[]}\n```\n'
            'middle\n'
            '```chart\n{"type":"bar","data":[]}\n```'
        )
        results = [
            {"success": True, "url": "https://img.example.com/pie.png", "type": "pie"},
            {"success": True, "url": "https://img.example.com/bar.png", "type": "bar"},
        ]
        new_md = replace_chart_blocks_with_images(md, results)
        assert "![pie]" in new_md
        assert "![bar]" in new_md
        assert "```chart" not in new_md

    def test_no_results_preserves_blocks(self):
        md = '```chart\n{"type":"pie","data":[]}\n```'
        new_md = replace_chart_blocks_with_images(md, [])
        assert "```chart" in new_md


# ==================== chart_visualization_skill (integration) ====================

class TestChartVisualizationSkill:

    def test_no_chart_blocks_returns_unmodified(self):
        result = chart_visualization_skill({"markdown": "# Hello\nNo charts here"})
        assert result["modified"] is False
        assert result["charts"] == []

    def test_string_input_accepted(self):
        result = chart_visualization_skill("# Hello\nNo charts here")
        assert result["modified"] is False

    @patch("services.blog_generator.skills.chart_visualization.ChartService")
    def test_with_chart_blocks_calls_service(self, MockService):
        mock_instance = MockService.return_value
        from services.chart_service import ChartResult
        mock_instance.generate.return_value = ChartResult(
            success=True, url="https://img.example.com/pie.png"
        )

        md = '```chart\n{"type": "pie", "data": [{"category": "A", "value": 1}]}\n```'
        result = chart_visualization_skill({"markdown": md})
        assert result["modified"] is True
        assert len(result["charts"]) == 1
        assert result["charts"][0]["success"] is True
        mock_instance.generate.assert_called_once()

    @patch("services.blog_generator.skills.chart_visualization.ChartService")
    def test_service_failure_handled(self, MockService):
        mock_instance = MockService.return_value
        from services.chart_service import ChartResult
        mock_instance.generate.return_value = ChartResult(
            success=False, error="API error"
        )

        md = '```chart\n{"type": "pie", "data": [{"category": "A", "value": 1}]}\n```'
        result = chart_visualization_skill({"markdown": md})
        assert result["modified"] is True
        assert result["charts"][0]["success"] is False
        assert "图表生成失败" in result["markdown"]
