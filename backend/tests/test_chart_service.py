"""
图表可视化服务 — 单元测试

TDD Red: 先写测试，再实现 ChartService。
运行: cd backend && python -m pytest tests/test_chart_service.py -v
"""
import pytest
from unittest.mock import MagicMock, patch

from services.chart_service import (
    ChartService,
    ChartResult,
    CHART_TYPE_MAP,
    MAP_CHART_TYPES,
    ChartTheme,
)


# ==================== 类型映射 ====================

class TestChartTypeMap:

    def test_all_26_types_mapped(self):
        assert len(CHART_TYPE_MAP) == 26

    def test_map_types_are_subset(self):
        for mt in MAP_CHART_TYPES:
            assert mt in CHART_TYPE_MAP

    @pytest.mark.parametrize("chart_type,expected", [
        ("pie", "pie"),
        ("line", "line"),
        ("bar", "bar"),
        ("column", "column"),
        ("sankey", "sankey"),
        ("network", "network-graph"),
        ("fishbone", "fishbone-diagram"),
        ("mind_map", "mind-map"),
        ("org_chart", "organization-chart"),
        ("word_cloud", "word-cloud"),
        ("flow", "flow-diagram"),
        ("dual_axes", "dual-axes"),
    ])
    def test_type_mapping_values(self, chart_type, expected):
        assert CHART_TYPE_MAP[chart_type] == expected

    def test_map_chart_types_count(self):
        assert MAP_CHART_TYPES == {"district_map", "path_map", "pin_map"}


# ==================== ChartTheme ====================

class TestChartTheme:

    def test_theme_values(self):
        assert ChartTheme.DEFAULT == "default"
        assert ChartTheme.ACADEMY == "academy"
        assert ChartTheme.DARK == "dark"


# ==================== ChartService ====================

class TestChartService:

    @pytest.fixture
    def service(self):
        return ChartService(vis_server="https://test.example.com/api")

    def test_unknown_type_returns_error(self, service):
        result = service.generate("nonexistent", {"data": []})
        assert not result.success
        assert "未知图表类型" in result.error

    def test_generate_pie_chart_success(self, service):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "resultObj": "https://antv.example.com/chart/abc123.png",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(service._client, "post", return_value=mock_resp):
            result = service.generate("pie", {
                "data": [{"category": "A", "value": 60}, {"category": "B", "value": 40}],
                "title": "Test Pie",
            })
        assert result.success
        assert "antv.example.com" in result.url

    def test_generate_line_chart_success(self, service):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "resultObj": "https://antv.example.com/chart/line001.png",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(service._client, "post", return_value=mock_resp):
            result = service.generate("line", {
                "data": [{"x": 1, "y": 10}, {"x": 2, "y": 20}],
            })
        assert result.success
        assert result.url == "https://antv.example.com/chart/line001.png"

    def test_api_error_handled(self, service):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": False,
            "errorMessage": "Invalid data format",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(service._client, "post", return_value=mock_resp):
            result = service.generate("line", {"data": []})
        assert not result.success
        assert "Invalid data format" in result.error

    def test_timeout_handled(self, service):
        import httpx
        with patch.object(service._client, "post", side_effect=httpx.TimeoutException("timeout")):
            result = service.generate("bar", {"data": []})
        assert not result.success
        assert "超时" in result.error

    def test_network_error_handled(self, service):
        import httpx
        with patch.object(service._client, "post", side_effect=httpx.ConnectError("refused")):
            result = service.generate("bar", {"data": []})
        assert not result.success
        assert result.error  # some error message

    def test_generate_map_uses_map_path(self, service):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "resultObj": {
                "content": [{"type": "text", "text": "https://map.example.com/map.png"}]
            },
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(service._client, "post", return_value=mock_resp) as mock_post:
            result = service.generate("district_map", {"data": {"region": "china"}})

        assert result.success
        assert "map.example.com" in result.url
        # Verify map-specific payload structure
        call_args = mock_post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        assert "tool" in payload
        assert "input" in payload

    def test_chart_payload_structure(self, service):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "resultObj": "https://x.com/c.png"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(service._client, "post", return_value=mock_resp) as mock_post:
            service.generate("pie", {"data": [{"category": "A", "value": 1}]})

        call_args = mock_post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        assert payload["type"] == "pie"
        assert payload["source"] == "vibe-blog-chart"

    def test_result_stores_spec(self, service):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "resultObj": "https://x.com/c.png"}
        mock_resp.raise_for_status = MagicMock()

        spec = {"data": [{"category": "A", "value": 1}], "title": "Test"}
        with patch.object(service._client, "post", return_value=mock_resp):
            result = service.generate("pie", spec)
        assert result.success
        assert result.spec is not None
