"""
37.13 写作模板体系 — PromptComposer

将 WritingTemplate 补丁 + Style 风格指南 + 运行时参数组合为完整 Prompt。

组合顺序：
1. 基础角色定义（base_prompt）
2. 写作模板指令（template.prompt_patches[agent_name]）
3. 风格指令（style.style_guide）
4. 运行时上下文（runtime_context）
"""
from typing import Optional


class PromptComposer:
    """Prompt 组合器"""

    def compose(
        self,
        agent_name: str,
        base_prompt: str = "",
        template: Optional[dict] = None,
        style: Optional[dict] = None,
        runtime_context: str = "",
    ) -> str:
        """组合完整 Prompt

        Args:
            agent_name: Agent 标识（planner / writer / reviewer 等）
            base_prompt: 基础角色定义文本
            template: WritingTemplate JSON（可为 None）
            style: Style JSON（可为 None）
            runtime_context: 运行时参数文本（任务描述等）

        Returns:
            组合后的完整 Prompt
        """
        parts = []

        # 1. 基础角色定义
        if base_prompt:
            parts.append(base_prompt)

        # 2. 写作模板指令
        template_patch = None
        if template and "prompt_patches" in template:
            template_patch = template["prompt_patches"].get(agent_name)
        if template_patch:
            parts.append(f"\n## 写作结构要求\n{template_patch}")

        # 3. 风格指令
        style_guide = None
        if style:
            style_guide = style.get("style_guide")
        if style_guide:
            parts.append(f"\n## 写作风格要求\n请严格遵循以下写作风格：\n{style_guide}")

        # 4. 运行时上下文
        if runtime_context:
            parts.append(f"\n{runtime_context}")

        return "\n".join(parts)
