"""
37.16 学习笔记衍生物 — StudyNoteSkill

从博客 Markdown 提取要点，生成精简学习笔记。
"""
import re
from typing import Dict, List
from ..skills.registry import SkillRegistry


def generate_study_note_from_markdown(markdown: str) -> Dict:
    """从 Markdown 提取标题和首句，生成精简学习笔记"""
    key_points: List[str] = []
    note_parts: List[str] = []
    lines = markdown.strip().split("\n")

    current_heading = ""
    first_sentence = ""

    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.+)", line.strip())
        if m:
            # 保存上一个
            if current_heading and first_sentence:
                key_points.append(current_heading)
                note_parts.append(f"- **{current_heading}**: {first_sentence}")
            current_heading = m.group(2).strip()
            first_sentence = ""
        else:
            text = line.strip()
            if text and not first_sentence:
                # 取第一个非空行作为摘要
                first_sentence = text[:200]

    # 最后一个
    if current_heading and first_sentence:
        key_points.append(current_heading)
        note_parts.append(f"- **{current_heading}**: {first_sentence}")

    note = "# 学习笔记\n\n" + "\n".join(note_parts) if note_parts else ""
    return {"note": note, "key_points": key_points}


@SkillRegistry.register(
    name="study_note",
    description="从博客生成学习笔记",
    input_type="markdown",
    output_type="markdown",
    post_process=True,
    auto_run=False,
    timeout=30,
)
def study_note_skill(data) -> Dict:
    markdown = data if isinstance(data, str) else data.get("markdown", "")
    return generate_study_note_from_markdown(markdown)
