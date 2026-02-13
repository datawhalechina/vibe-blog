"""
AgentDispatcher 单元测试
TDD: 测试用例 AD1-AD20
所有 Agent 均 Mock，只测试 Dispatcher 的路由和参数传递逻辑。
"""
import pytest
from unittest.mock import MagicMock, patch
from services.chat.writing_session import WritingSession, WritingSessionManager
from services.chat.agent_dispatcher import AgentDispatcher


@pytest.fixture
def session_mgr():
    return WritingSessionManager(db_path=":memory:")


@pytest.fixture
def session_with_outline(session_mgr):
    """带大纲和已写章节的会话"""
    s = session_mgr.create(topic="AI 入门指南")
    session_mgr.update(s.session_id, outline={
        "title": "AI 入门指南",
        "sections": [
            {"id": "s1", "title": "什么是 AI", "key_points": ["定义"]},
            {"id": "s2", "title": "机器学习", "key_points": ["监督学习"]},
            {"id": "s3", "title": "深度学习", "key_points": ["CNN"]},
        ]
    }, sections=[
        {"id": "s1", "title": "什么是 AI", "content": "AI 是人工智能的缩写..."},
    ], search_results=[
        {"title": "AI Wiki", "content": "Artificial intelligence..."},
    ])
    return session_mgr.get(s.session_id)


@pytest.fixture
def dispatcher():
    """Mock 所有 Agent 的 Dispatcher"""
    with patch('services.chat.agent_dispatcher.ResearcherAgent') as MockRes, \
         patch('services.chat.agent_dispatcher.SearchCoordinator') as MockSC, \
         patch('services.chat.agent_dispatcher.PlannerAgent') as MockPlan, \
         patch('services.chat.agent_dispatcher.WriterAgent') as MockWriter, \
         patch('services.chat.agent_dispatcher.CoderAgent') as MockCoder, \
         patch('services.chat.agent_dispatcher.ArtistAgent') as MockArtist, \
         patch('services.chat.agent_dispatcher.ReviewerAgent') as MockReviewer, \
         patch('services.chat.agent_dispatcher.FactCheckAgent') as MockFC, \
         patch('services.chat.agent_dispatcher.HumanizerAgent') as MockHuman, \
         patch('services.chat.agent_dispatcher.AssemblerAgent') as MockAssembler:
        d = AgentDispatcher(llm_client=MagicMock(), search_service=MagicMock())
        yield d


# ========== 调研阶段 AD1-AD3 ==========

class TestResearch:
    def test_ad1_init_all_agents(self, dispatcher):
        """AD1: 所有 Agent 实例化成功"""
        assert dispatcher.researcher is not None
        assert dispatcher.search_coordinator is not None
        assert dispatcher.planner is not None
        assert dispatcher.writer is not None
        assert dispatcher.coder is not None
        assert dispatcher.artist is not None
        assert dispatcher.reviewer is not None
        assert dispatcher.factcheck_agent is not None
        assert dispatcher.humanizer is not None
        assert dispatcher.assembler is not None

    def test_ad2_search(self, dispatcher, session_mgr):
        """AD2: search() 调用 ResearcherAgent.search()"""
        session = session_mgr.create(topic="AI 入门")
        dispatcher.researcher.search.return_value = [{"title": "result1"}]
        result = dispatcher.search(session)
        assert "search_results" in result
        assert len(result["search_results"]) == 1
        dispatcher.researcher.search.assert_called_once()

    def test_ad3_detect_knowledge_gaps(self, dispatcher, session_mgr):
        """AD3: detect_knowledge_gaps() 调用 SearchCoordinator"""
        session = session_mgr.create(topic="AI 入门")
        dispatcher.search_coordinator.detect_knowledge_gaps.return_value = [
            {"gap": "缺少 CNN 相关知识"}
        ]
        result = dispatcher.detect_knowledge_gaps(session, content="一些内容")
        assert "knowledge_gaps" in result
        assert len(result["knowledge_gaps"]) == 1


# ========== 大纲阶段 AD4-AD6 ==========

class TestOutline:
    def test_ad4_generate_outline(self, dispatcher, session_mgr):
        """AD4: generate_outline() 调用 PlannerAgent"""
        session = session_mgr.create(topic="AI 入门")
        dispatcher.planner.generate_outline.return_value = {
            "title": "AI 入门指南",
            "sections": [{"id": "s1", "title": "简介"}],
        }
        result = dispatcher.generate_outline(session)
        assert "outline" in result
        assert result["outline"]["title"] == "AI 入门指南"
        dispatcher.planner.generate_outline.assert_called_once()

    def test_ad5_edit_outline_title(self, dispatcher, session_with_outline):
        """AD5: edit_outline() 修改标题"""
        result = dispatcher.edit_outline(session_with_outline, {"title": "新标题"})
        assert result["outline"]["title"] == "新标题"

    def test_ad6_edit_outline_add_remove_section(self, dispatcher, session_with_outline):
        """AD6: edit_outline() 添加/删除章节"""
        # 添加
        result = dispatcher.edit_outline(session_with_outline, {
            "add_section": {"id": "s4", "title": "新章节"}
        })
        assert len(result["outline"]["sections"]) == 4
        # 删除
        result = dispatcher.edit_outline(session_with_outline, {
            "remove_section_id": "s3"
        })
        ids = [s["id"] for s in result["outline"]["sections"]]
        assert "s3" not in ids


# ========== 写作阶段 AD7-AD12 ==========

class TestWriting:
    def test_ad7_write_section(self, dispatcher, session_with_outline):
        """AD7: write_section() 调用 WriterAgent.write_section()"""
        dispatcher.writer.write_section.return_value = {
            "id": "s2", "title": "机器学习", "content": "机器学习是..."
        }
        result = dispatcher.write_section(session_with_outline, "s2")
        assert "section" in result
        dispatcher.writer.write_section.assert_called_once()

    def test_ad8_write_section_with_context(self, dispatcher, session_with_outline):
        """AD8: write_section() 传递上下文（前章节摘要）"""
        dispatcher.writer.write_section.return_value = {"id": "s2", "content": "..."}
        dispatcher.write_section(session_with_outline, "s2")
        call_kwargs = dispatcher.writer.write_section.call_args
        # s1 已写，s2 应该收到 s1 的摘要作为 previous_section_summary
        assert call_kwargs.kwargs.get("previous_section_summary") or \
               (len(call_kwargs.args) > 1 and call_kwargs.args[1])

    def test_ad9_edit_section(self, dispatcher, session_with_outline):
        """AD9: edit_section() 调用 WriterAgent.improve_section()"""
        dispatcher.writer.improve_section.return_value = "改进后的内容"
        result = dispatcher.edit_section(session_with_outline, "s1", "请增加更多示例")
        assert "content" in result
        dispatcher.writer.improve_section.assert_called_once()

    def test_ad10_enhance_section(self, dispatcher, session_with_outline):
        """AD10: enhance_section() 调用 WriterAgent.enhance_section()"""
        dispatcher.writer.enhance_section.return_value = "增强后的内容"
        result = dispatcher.enhance_section(session_with_outline, "s1")
        assert "content" in result
        dispatcher.writer.enhance_section.assert_called_once()

    def test_ad11_write_nonexistent_section(self, dispatcher, session_with_outline):
        """AD11: write_section() section_id 不存在返回错误"""
        result = dispatcher.write_section(session_with_outline, "s999")
        assert "error" in result

    def test_ad12_edit_unwritten_section(self, dispatcher, session_with_outline):
        """AD12: edit_section() 章节未写作返回错误"""
        result = dispatcher.edit_section(session_with_outline, "s2", "修改")
        assert "error" in result


# ========== 代码/配图/质量/组装 AD13-AD20 ==========

class TestCodeAndQuality:
    def test_ad13_generate_code(self, dispatcher, session_with_outline):
        """AD13: generate_code() 调用 CoderAgent"""
        dispatcher.coder.generate_code.return_value = {"code": "print('hello')"}
        result = dispatcher.generate_code(session_with_outline, "打印 hello")
        assert "code_block" in result
        dispatcher.coder.generate_code.assert_called_once()

    def test_ad14_generate_image(self, dispatcher, session_with_outline):
        """AD14: generate_image() 调用 ArtistAgent"""
        dispatcher.artist.generate_image.return_value = {"url": "http://img.png"}
        result = dispatcher.generate_image(session_with_outline, "AI 架构图")
        assert "image" in result
        dispatcher.artist.generate_image.assert_called_once()

    def test_ad15_review(self, dispatcher, session_with_outline):
        """AD15: review() 组装全文后调用 ReviewerAgent"""
        dispatcher.reviewer.review.return_value = {"score": 85, "issues": []}
        result = dispatcher.review(session_with_outline)
        assert "review" in result
        dispatcher.reviewer.review.assert_called_once()

    def test_ad16_factcheck(self, dispatcher, session_with_outline):
        """AD16: factcheck() 调用 FactCheckAgent"""
        dispatcher.factcheck_agent.check.return_value = {"claims": [], "score": 90}
        result = dispatcher.factcheck(session_with_outline)
        assert "factcheck" in result
        dispatcher.factcheck_agent.check.assert_called_once()

    def test_ad17_humanize_single_section(self, dispatcher, session_with_outline):
        """AD17: humanize() 指定 section_id"""
        dispatcher.humanizer._rewrite_section.return_value = {"rewritten": "自然的内容"}
        result = dispatcher.humanize(session_with_outline, section_id="s1")
        assert "humanized" in result
        assert result["section_id"] == "s1"

    def test_ad18_humanize_all(self, dispatcher, session_with_outline):
        """AD18: humanize() 全文"""
        dispatcher.humanizer._rewrite_section.return_value = {"rewritten": "自然的内容"}
        result = dispatcher.humanize(session_with_outline)
        assert "humanized_sections" in result

    def test_ad19_assemble(self, dispatcher, session_with_outline):
        """AD19: assemble() 调用 AssemblerAgent"""
        dispatcher.assembler.assemble.return_value = {"final_markdown": "# AI\n..."}
        result = dispatcher.assemble(session_with_outline)
        assert "markdown" in result
        dispatcher.assembler.assemble.assert_called_once()

    def test_ad20_get_preview(self, dispatcher, session_with_outline):
        """AD20: get_preview() 返回已写章节拼接"""
        result = dispatcher.get_preview(session_with_outline)
        assert "preview" in result
        assert "AI 入门指南" in result["preview"]
        assert result["section_count"] == 1
