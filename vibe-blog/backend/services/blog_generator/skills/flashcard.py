"""
37.16 闪卡衍生物 — FlashcardSkill

从博客 Markdown 提取关键概念，生成 Q&A 闪卡。
"""
import re
from typing import Dict, List
from ..skills.registry import SkillRegistry


def generate_flashcards_from_markdown(markdown: str) -> Dict:
    """从 Markdown 提取标题+段落，生成 Q&A 闪卡"""
    cards: List[Dict] = []
    lines = markdown.strip().split("\n")

    current_heading = ""
    current_content: List[str] = []

    for line in lines:
        m = re.match(r"^#{1,6}\s+(.+)", line.strip())
        if m:
            # 保存上一个段落
            if current_heading and current_content:
                content = " ".join(current_content).strip()
                if len(content) > 10:
                    cards.append({
                        "question": f"什么是{current_heading}？",
                        "answer": content[:500],
                    })
            current_heading = m.group(1).strip()
            current_content = []
        else:
            text = line.strip()
            if text:
                current_content.append(text)

    # 最后一个段落
    if current_heading and current_content:
        content = " ".join(current_content).strip()
        if len(content) > 10:
            cards.append({
                "question": f"什么是{current_heading}？",
                "answer": content[:500],
            })

    return {"cards": cards}


@SkillRegistry.register(
    name="flashcard",
    description="从博客生成闪卡",
    input_type="markdown",
    output_type="json",
    post_process=True,
    auto_run=False,
    timeout=30,
)
def flashcard_skill(data) -> Dict:
    markdown = data if isinstance(data, str) else data.get("markdown", "")
    return generate_flashcards_from_markdown(markdown)
