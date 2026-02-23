"""
图表可视化 Skill — 从博客内容中提取 chart 代码块并生成可视化图片

注册为后处理 Skill，在博客生成完成后触发。
支持 26 种图表类型，通过 AntV Studio API 渲染。
"""
import json
import logging
import re
from typing import Any, Dict, List

from ..skills.registry import SkillRegistry
from ...chart_service import ChartService

logger = logging.getLogger(__name__)


def extract_chart_blocks(markdown: str) -> List[Dict[str, Any]]:
    """从 Markdown 中提取 ```chart JSON 代码块

    要求每个代码块包含 "type" 和 "data" 字段。
    """
    pattern = r"```chart\s*\n(.*?)\n```"
    blocks = re.findall(pattern, markdown, re.DOTALL)
    results = []
    for block in blocks:
        try:
            spec = json.loads(block.strip())
            if "type" in spec and "data" in spec:
                results.append(spec)
        except json.JSONDecodeError:
            logger.warning(f"无法解析 chart 代码块: {block[:100]}...")
    return results


def replace_chart_blocks_with_images(markdown: str, chart_results: List[Dict]) -> str:
    """将 ```chart 代码块替换为图片 Markdown 或失败注释"""
    idx = 0

    def replacer(match):
        nonlocal idx
        if idx < len(chart_results):
            r = chart_results[idx]
            idx += 1
            if r["success"] and r["url"]:
                title = r.get("type", "chart")
                return f'![{title}]({r["url"]})'
            else:
                return f'<!-- 图表生成失败: {r.get("error", "unknown")} -->\n{match.group(0)}'
        return match.group(0)

    return re.sub(r"```chart\s*\n.*?\n```", replacer, markdown, flags=re.DOTALL)


@SkillRegistry.register(
    name="chart_visualization",
    description="从博客中提取数据图表规范并生成可视化图片",
    input_type="markdown",
    output_type="markdown",
    post_process=True,
    auto_run=False,
    timeout=120,
)
def chart_visualization_skill(data: Any) -> Dict:
    """提取 ```chart 代码块 → 调用 ChartService 生成图片 → 替换回 Markdown"""
    markdown = data if isinstance(data, str) else data.get("markdown", "")
    chart_specs = extract_chart_blocks(markdown)
    if not chart_specs:
        return {"modified": False, "markdown": markdown, "charts": []}

    service = ChartService()
    results = []
    for spec in chart_specs:
        chart_type = spec.pop("type", "")
        result = service.generate(chart_type, spec)
        results.append({
            "type": chart_type,
            "success": result.success,
            "url": result.url,
            "error": result.error,
        })

    new_markdown = replace_chart_blocks_with_images(markdown, results)
    return {"modified": True, "markdown": new_markdown, "charts": results}
