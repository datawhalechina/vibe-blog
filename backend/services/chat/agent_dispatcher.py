"""
AgentDispatcher — Agent 方法分发器
将对话式写作的细粒度请求路由到对应的 Agent 底层方法。
不走 LangGraph pipeline，直接调用 Agent 内部方法。
"""
import logging
from typing import Optional, Dict, Any, List

from services.blog_generator.agents import (
    ResearcherAgent, PlannerAgent, WriterAgent, CoderAgent,
    ArtistAgent, ReviewerAgent, AssemblerAgent, SearchCoordinator,
)
from services.blog_generator.agents.factcheck import FactCheckAgent
from services.blog_generator.agents.humanizer import HumanizerAgent
from services.chat.writing_session import WritingSession

logger = logging.getLogger(__name__)


class AgentDispatcher:
    """细粒度 Agent 分发器 — 每个方法对应一个对话式写作步骤"""

    def __init__(self, llm_client, search_service=None, knowledge_service=None):
        self.researcher = ResearcherAgent(llm_client, search_service, knowledge_service)
        self.search_coordinator = SearchCoordinator(llm_client, search_service) if search_service else None
        self.planner = PlannerAgent(llm_client)
        self.writer = WriterAgent(llm_client)
        self.coder = CoderAgent(llm_client)
        self.artist = ArtistAgent(llm_client)
        self.reviewer = ReviewerAgent(llm_client)
        self.factcheck_agent = FactCheckAgent(llm_client)
        self.humanizer = HumanizerAgent(llm_client)
        self.assembler = AssemblerAgent()

    # ========== 调研阶段 ==========

    def search(self, session: WritingSession, **kwargs) -> dict:
        """调研 — 调用 ResearcherAgent.search()"""
        results = self.researcher.search(
            topic=session.topic,
            target_audience=session.target_audience,
            **kwargs,
        )
        return {"search_results": results}

    def detect_knowledge_gaps(self, session: WritingSession, content: str = "") -> dict:
        """知识缺口检测 — 调用 SearchCoordinator.detect_knowledge_gaps()"""
        if not self.search_coordinator:
            return {"knowledge_gaps": [], "error": "搜索服务不可用"}
        gaps = self.search_coordinator.detect_knowledge_gaps(
            content=content,
            existing_knowledge=session.research_summary or "",
            topic=session.topic,
        )
        return {"knowledge_gaps": gaps}

    # ========== 大纲阶段 ==========

    def generate_outline(self, session: WritingSession) -> dict:
        """生成大纲 — 调用 PlannerAgent.generate_outline()"""
        outline = self.planner.generate_outline(
            topic=session.topic,
            article_type=session.article_type,
            target_audience=session.target_audience,
            target_length=session.target_length,
            background_knowledge=session.research_summary or "",
            key_concepts=session.key_concepts or [],
        )
        return {"outline": outline}

    def edit_outline(self, session: WritingSession, changes: dict) -> dict:
        """编辑大纲 — 直接修改 outline 结构"""
        outline = dict(session.outline) if session.outline else {}
        if "title" in changes:
            outline["title"] = changes["title"]
        if "add_section" in changes:
            sections = outline.get("sections", [])
            sections.append(changes["add_section"])
            outline["sections"] = sections
        if "remove_section_id" in changes:
            sid = changes["remove_section_id"]
            outline["sections"] = [
                s for s in outline.get("sections", []) if s.get("id") != sid
            ]
        if "update_section" in changes:
            upd = changes["update_section"]
            for s in outline.get("sections", []):
                if s.get("id") == upd.get("id"):
                    s.update(upd)
                    break
        return {"outline": outline}

    # ========== 写作阶段 ==========

    def _find_section_outline(self, session: WritingSession, section_id: str) -> Optional[dict]:
        """从 outline 中查找章节定义"""
        if not session.outline:
            return None
        for s in session.outline.get("sections", []):
            if s.get("id") == section_id:
                return s
        return None

    def _find_written_section(self, session: WritingSession, section_id: str) -> Optional[dict]:
        """从已写章节中查找"""
        for s in (session.sections or []):
            if s.get("id") == section_id:
                return s
        return None

    def write_section(self, session: WritingSession, section_id: str) -> dict:
        """写作单个章节 — 调用 WriterAgent.write_section()"""
        section_outline = self._find_section_outline(session, section_id)
        if not section_outline:
            return {"error": f"章节 {section_id} 不在大纲中"}

        # 构建上下文
        sections = session.outline.get("sections", [])
        idx = next((i for i, s in enumerate(sections) if s.get("id") == section_id), 0)
        prev_summary = ""
        if idx > 0:
            prev = self._find_written_section(session, sections[idx - 1].get("id", ""))
            if prev:
                prev_summary = prev.get("content", "")[:200]

        result = self.writer.write_section(
            section_outline=section_outline,
            previous_section_summary=prev_summary,
            background_knowledge=session.research_summary or "",
            search_results=session.search_results or [],
        )
        return {"section": result}

    def edit_section(self, session: WritingSession, section_id: str, instructions: str) -> dict:
        """编辑章节 — 调用 WriterAgent.improve_section()"""
        written = self._find_written_section(session, section_id)
        if not written:
            return {"error": f"章节 {section_id} 尚未写作"}
        result = self.writer.improve_section(
            original_content=written.get("content", ""),
            critique={"suggestions": [instructions]},
            section_title=written.get("title", ""),
        )
        return {"content": result}

    def enhance_section(self, session: WritingSession, section_id: str) -> dict:
        """增强章节 — 调用 WriterAgent.enhance_section()"""
        written = self._find_written_section(session, section_id)
        if not written:
            return {"error": f"章节 {section_id} 尚未写作"}
        result = self.writer.enhance_section(
            original_content=written.get("content", ""),
            vague_points=[{"point": "内容需要更详细的解释和示例"}],
            section_title=written.get("title", ""),
        )
        return {"content": result}

    # ========== 代码 & 配图 ==========

    def generate_code(self, session: WritingSession, description: str,
                      language: str = "python") -> dict:
        """生成代码 — 调用 CoderAgent.generate_code()"""
        result = self.coder.generate_code(
            code_description=description,
            context=session.topic,
            language=language,
        )
        return {"code_block": result}

    def generate_image(self, session: WritingSession, description: str,
                       image_type: str = "diagram") -> dict:
        """生成配图 — 调用 ArtistAgent.generate_image()"""
        result = self.artist.generate_image(
            image_type=image_type,
            description=description,
            context=session.topic,
            article_title=session.outline.get("title", "") if session.outline else "",
        )
        return {"image": result}

    # ========== 质量检查 ==========

    def review(self, session: WritingSession) -> dict:
        """审核 — 调用 ReviewerAgent.review()"""
        all_content = "\n\n".join(
            s.get("content", "") for s in (session.sections or [])
        )
        result = self.reviewer.review(
            document=all_content,
            outline=session.outline or {},
        )
        return {"review": result}

    def factcheck(self, session: WritingSession) -> dict:
        """事实核查 — 调用 FactCheckAgent.check()"""
        all_content = "\n\n".join(
            s.get("content", "") for s in (session.sections or [])
        )
        all_evidence = "\n\n".join(
            f"[{r.get('title', '')}] {r.get('content', '')[:300]}"
            for r in (session.search_results or [])
        )
        result = self.factcheck_agent.check(
            all_content=all_content,
            all_evidence=all_evidence or "(无证据)",
        )
        return {"factcheck": result}

    def humanize(self, session: WritingSession, section_id: str = None) -> dict:
        """去AI味 — 调用 HumanizerAgent._rewrite_section()"""
        if section_id:
            written = self._find_written_section(session, section_id)
            if not written:
                return {"error": f"章节 {section_id} 尚未写作"}
            result = self.humanizer._rewrite_section(
                content=written.get("content", ""),
                audience_adaptation=session.target_audience,
            )
            return {"humanized": result, "section_id": section_id}
        # 全文 humanize
        results = []
        for s in (session.sections or []):
            r = self.humanizer._rewrite_section(
                content=s.get("content", ""),
                audience_adaptation=session.target_audience,
            )
            results.append({"section_id": s.get("id"), "humanized": r})
        return {"humanized_sections": results}

    # ========== 组装 & 管理 ==========

    def assemble(self, session: WritingSession) -> dict:
        """组装最终文档 — 调用 AssemblerAgent.assemble()"""
        result = self.assembler.assemble(
            outline=session.outline or {},
            sections=session.sections or [],
            code_blocks=session.code_blocks or [],
            images=session.images or [],
            search_results=session.search_results or [],
        )
        return {"markdown": result}

    def get_preview(self, session: WritingSession) -> dict:
        """获取预览 — 返回当前已写章节的 Markdown"""
        parts = []
        if session.outline:
            parts.append(f"# {session.outline.get('title', session.topic)}\n")
        for s in (session.sections or []):
            parts.append(f"## {s.get('title', '')}\n\n{s.get('content', '')}\n")
        return {"preview": "\n".join(parts), "section_count": len(session.sections or [])}
