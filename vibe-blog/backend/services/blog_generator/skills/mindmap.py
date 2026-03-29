"""
37.16 思维导图衍生物 — MindMapSkill

从博客 Markdown 提取标题层级，生成结构化思维导图 JSON。
"""
import re
from typing import Dict, List
from ..skills.registry import SkillRegistry


def generate_mindmap_from_markdown(markdown: str) -> Dict:
    """从 Markdown 标题层级生成思维导图节点和边"""
    nodes: List[Dict] = []
    edges: List[Dict] = []
    node_id = 0

    lines = markdown.strip().split("\n")
    stack: List[int] = []  # (node_id) stack by heading level

    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.+)", line.strip())
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()

        current_id = node_id
        nodes.append({"id": current_id, "label": title, "level": level})
        node_id += 1

        # 找到父节点：stack 中最后一个 level < 当前 level 的
        while stack and nodes[stack[-1]]["level"] >= level:
            stack.pop()

        if stack:
            parent_id = stack[-1]
            edges.append({"source": parent_id, "target": current_id})

        stack.append(current_id)

    return {"nodes": nodes, "edges": edges}


@SkillRegistry.register(
    name="mindmap",
    description="从博客生成思维导图",
    input_type="markdown",
    output_type="json",
    post_process=True,
    auto_run=False,
    timeout=30,
)
def mindmap_skill(data) -> Dict:
    markdown = data if isinstance(data, str) else data.get("markdown", "")
    return generate_mindmap_from_markdown(markdown)
