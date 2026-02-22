"""
Prose Editor Agent — 6 种 AI 行内编辑模式

编辑模式:
- continue: 续写 — 从选中文本末尾继续
- improve: 润色 — 提升文字质量
- shorter: 缩短 — 精简保留核心
- longer: 扩展 — 增加细节深度
- fix: 修正 — 修复语法拼写
- zap: 自由指令 — 按用户命令编辑
"""
import logging
from typing import Literal

from infrastructure.prompts import get_prompt_manager

logger = logging.getLogger(__name__)

ProseOption = Literal["continue", "improve", "shorter", "longer", "fix", "zap"]

VALID_OPTIONS = {"continue", "improve", "shorter", "longer", "fix", "zap"}


class ProseEditorAgent:
    """Prose 行内编辑 Agent — 通过 option 参数路由到对应编辑逻辑"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def edit(
        self,
        content: str,
        option: ProseOption,
        command: str = "",
        memory_context: str = "",
    ) -> str:
        """统一编辑入口 — 路由到对应模式"""
        if option not in VALID_OPTIONS:
            raise ValueError(f"未知编辑模式: {option}")

        logger.info(f"[ProseEditor] 执行 {option} 编辑 ({len(content)} 字)")
        return self._call_llm(option, content, command=command, memory_context=memory_context)

    def edit_stream(
        self,
        content: str,
        option: ProseOption,
        command: str = "",
        memory_context: str = "",
    ):
        """流式编辑入口 — 返回 generator 或回退到同步"""
        if option not in VALID_OPTIONS:
            raise ValueError(f"未知编辑模式: {option}")

        system_prompt = self._render_prompt(option, memory_context)
        user_prompt = self._build_user_prompt(content, option, command)

        if hasattr(self.llm, 'chat_stream') and callable(self.llm.chat_stream):
            return self.llm.chat_stream(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tier="fast",
                caller="prose_editor",
            )
        # 回退到同步
        result = self.edit(content, option, command, memory_context)
        return iter([result])

    def _render_prompt(self, option: str, memory_context: str = "") -> str:
        """渲染 system prompt 模板"""
        pm = get_prompt_manager()
        return pm.render(f"prose/{option}", memory_context=memory_context)

    @staticmethod
    def _build_user_prompt(content: str, option: str, command: str = "") -> str:
        """构建 user prompt（对齐 DeerFlow 各节点的拼接逻辑）"""
        if option == "continue":
            return content
        elif option == "zap":
            return f"For this text: {content}.\nYou have to respect the command: {command}"
        else:
            return f"The existing text is: {content}"

    def _call_llm(self, option: str, content: str, command: str = "",
                  memory_context: str = "") -> str:
        """调用 LLM 执行编辑"""
        system_prompt = self._render_prompt(option, memory_context)
        user_prompt = self._build_user_prompt(content, option, command)
        return self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tier="fast",
            caller="prose_editor",
        )
