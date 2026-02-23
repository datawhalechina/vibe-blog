"""
图表可视化服务 — 26 种图表类型 + AntV Studio API 渲染

支持时序趋势、分类对比、占比关系、关系流向、层级结构、
地理空间、统计分布、专项可视化等全场景数据图表生成。
"""
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# 26 种图表类型 → AntV API type 映射
CHART_TYPE_MAP = {
    "area": "area",
    "bar": "bar",
    "boxplot": "boxplot",
    "column": "column",
    "district_map": "district-map",
    "dual_axes": "dual-axes",
    "fishbone": "fishbone-diagram",
    "flow": "flow-diagram",
    "funnel": "funnel",
    "histogram": "histogram",
    "line": "line",
    "liquid": "liquid",
    "mind_map": "mind-map",
    "network": "network-graph",
    "org_chart": "organization-chart",
    "path_map": "path-map",
    "pie": "pie",
    "pin_map": "pin-map",
    "radar": "radar",
    "sankey": "sankey",
    "scatter": "scatter",
    "spreadsheet": "spreadsheet",
    "treemap": "treemap",
    "venn": "venn",
    "violin": "violin",
    "word_cloud": "word-cloud",
}

MAP_CHART_TYPES = {"district_map", "path_map", "pin_map"}

DEFAULT_VIS_SERVER = "https://antv-studio.alipay.com/api/gpt-vis"


class ChartTheme(str, Enum):
    DEFAULT = "default"
    ACADEMY = "academy"
    DARK = "dark"


@dataclass
class ChartResult:
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None
    spec: Optional[Dict] = None


class ChartService:
    """图表生成服务 — 调用 AntV Studio API 渲染数据图表"""

    def __init__(self, vis_server: Optional[str] = None, service_id: Optional[str] = None):
        self.vis_server = vis_server or os.getenv("VIS_REQUEST_SERVER", DEFAULT_VIS_SERVER)
        self.service_id = service_id or os.getenv("VIS_SERVICE_ID")
        self._client = httpx.Client(timeout=30.0)

    def generate(self, chart_type: str, args: Dict[str, Any]) -> ChartResult:
        """生成图表，返回包含 URL 的 ChartResult"""
        api_type = CHART_TYPE_MAP.get(chart_type)
        if not api_type:
            return ChartResult(success=False, error=f"未知图表类型: {chart_type}")

        try:
            if chart_type in MAP_CHART_TYPES:
                return self._generate_map(chart_type, args)
            return self._generate_chart(api_type, args)
        except httpx.TimeoutException:
            return ChartResult(success=False, error=f"图表生成超时 (30s): {chart_type}")
        except Exception as e:
            logger.error(f"图表生成失败 [{chart_type}]: {e}")
            return ChartResult(success=False, error=str(e))

    def _generate_chart(self, api_type: str, args: Dict) -> ChartResult:
        payload = {"type": api_type, "source": "vibe-blog-chart", **args}
        resp = self._client.post(self.vis_server, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return ChartResult(success=False, error=data.get("errorMessage", "Unknown"))
        return ChartResult(success=True, url=data["resultObj"], spec=args)

    def _generate_map(self, tool: str, args: Dict) -> ChartResult:
        payload = {
            "serviceId": self.service_id,
            "tool": f"generate_{tool}",
            "input": args,
            "source": "vibe-blog-chart",
        }
        resp = self._client.post(self.vis_server, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return ChartResult(success=False, error=data.get("errorMessage", "Unknown"))
        result = data.get("resultObj", {})
        url = None
        if isinstance(result, dict) and "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    url = item.get("text")
                    break
        return ChartResult(success=True, url=url or str(result), spec=args)
