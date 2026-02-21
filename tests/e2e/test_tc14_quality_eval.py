"""
TC-14: 质量评估（QualityDialog）E2E 测试

验证：
1. 后端 POST /api/blog/{id}/evaluate 接口正确返回多维评分
2. 不存在的 blog 返回 404
3. 前端 QualityDialog 组件在 Generate 页面可触发并渲染（真实组件 + route mock）
"""
import json
import re
import pytest
import requests


EVALUATE_FIELDS = [
    "grade", "overall_score", "scores",
    "strengths", "weaknesses", "suggestions", "summary",
    "word_count", "citation_count", "image_count", "code_block_count",
]

SCORE_DIMENSIONS = [
    "factual_accuracy", "completeness", "coherence",
    "relevance", "citation_quality", "writing_quality",
]


def _get_blog_id(backend_url: str):
    """从历史记录获取一个可用的 blog_id"""
    resp = requests.get(f"{backend_url}/api/history?page=1&page_size=1", timeout=10)
    data = resp.json()
    records = data.get("records", [])
    if not records:
        return None
    return records[0].get("id") or records[0].get("task_id")


# ── 后端 API 测试 ──
# 评估接口调用 LLM，耗时较长。使用 class-scope fixture 缓存结果，避免重复调用。

@pytest.fixture(scope="module")
def evaluate_result():
    """调用一次评估接口，缓存结果供多个测试复用"""
    from e2e_utils import BACKEND_URL
    blog_id = _get_blog_id(BACKEND_URL)
    if not blog_id:
        pytest.skip("无历史记录，跳过评估 API 测试")

    resp = requests.post(f"{BACKEND_URL}/api/blog/{blog_id}/evaluate", timeout=180)
    return {"status_code": resp.status_code, "data": resp.json()}


class TestEvaluateAPI:
    """后端评估接口验证"""

    def test_evaluate_returns_success(self, evaluate_result):
        """POST /api/blog/{id}/evaluate 返回 success + evaluation"""
        assert evaluate_result["status_code"] == 200, \
            f"状态码异常: {evaluate_result['status_code']}, body: {str(evaluate_result['data'])[:200]}"

        data = evaluate_result["data"]
        assert data.get("success") is True, f"返回 success=False: {data}"
        assert "evaluation" in data, "响应缺少 evaluation 字段"

    def test_evaluate_has_all_fields(self, evaluate_result):
        """评估结果包含所有必要字段"""
        if evaluate_result["status_code"] != 200:
            pytest.skip(f"评估接口返回 {evaluate_result['status_code']}，可能 LLM 不可用")

        evaluation = evaluate_result["data"].get("evaluation", {})
        for field in EVALUATE_FIELDS:
            assert field in evaluation, f"缺少字段: {field}"

    def test_evaluate_has_6_score_dimensions(self, evaluate_result):
        """评分包含 6 个维度（对齐 DeerFlow LLMEvaluationScores）"""
        if evaluate_result["status_code"] != 200:
            pytest.skip(f"评估接口返回 {evaluate_result['status_code']}")

        scores = evaluate_result["data"].get("evaluation", {}).get("scores", {})
        for dim in SCORE_DIMENSIONS:
            assert dim in scores, f"缺少评分维度: {dim}"
            assert isinstance(scores[dim], (int, float)), f"{dim} 应为数字"

    def test_evaluate_grade_valid(self, evaluate_result):
        """等级在合法范围内"""
        if evaluate_result["status_code"] != 200:
            pytest.skip(f"评估接口返回 {evaluate_result['status_code']}")

        grade = evaluate_result["data"].get("evaluation", {}).get("grade", "")
        valid_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F", "N/A"}
        assert grade in valid_grades, f"非法等级: {grade}"

    def test_evaluate_nonexistent_blog(self, backend_url):
        """不存在的 blog_id 返回 404"""
        resp = requests.post(
            f"{backend_url}/api/blog/nonexistent_id_12345/evaluate", timeout=10
        )
        assert resp.status_code == 404, f"预期 404，实际: {resp.status_code}"


# ── 前端 UI 测试 ──
# 通过 Playwright route intercept mock 后端响应，在真实 Generate.vue 页面上操作真实 QualityDialog 组件。

# SSE mock 响应体：让 Generate 页面快速进入"已完成"状态
SSE_MOCK_BODY = (
    "event: connected\ndata: {}\n\n"
    'event: progress\ndata: {"stage":"start","message":"开始生成"}\n\n'
    'event: result\ndata: {"type":"outline_complete","data":{"title":"E2E 测试文章","sections_titles":["章节1","章节2"]}}\n\n'
    'event: complete\ndata: {"id":"mock-blog-id","markdown":"# 测试\\n\\n内容"}\n\n'
)

# Mock 评估数据
MOCK_EVALUATION = {
    "success": True,
    "evaluation": {
        "grade": "A-",
        "overall_score": 83,
        "scores": {
            "factual_accuracy": 85,
            "completeness": 78,
            "coherence": 92,
            "relevance": 88,
            "citation_quality": 70,
            "writing_quality": 85,
        },
        "strengths": ["代码示例丰富且可运行", "章节结构清晰有层次"],
        "weaknesses": ["引用来源偏少"],
        "suggestions": ["补充 3-5 个权威引用"],
        "summary": "文章结构清晰，建议补充更多引用。",
        "word_count": 3500,
        "citation_count": 8,
        "image_count": 4,
        "code_block_count": 6,
    },
}


class TestQualityDialogUI:
    """前端质量评估对话框 UI 验证 — 使用真实 QualityDialog 组件"""

    def _setup_route_mocks(self, page, base_url):
        """设置 route intercept：mock SSE stream 和 evaluate API"""

        # 拦截 SSE stream API
        def handle_sse(route):
            route.fulfill(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
                body=SSE_MOCK_BODY,
            )

        page.route("**/api/tasks/*/stream", handle_sse)

        # 拦截 evaluate API
        def handle_evaluate(route):
            route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps(MOCK_EVALUATION),
            )

        page.route("**/api/blog/*/evaluate", handle_evaluate)

        # 拦截任务状态 API（防止 404）
        def handle_task_status(route):
            route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "task": {
                        "id": "e2e-mock-task",
                        "status": "completed",
                        "topic": "E2E 测试文章",
                    }
                }),
            )

        page.route("**/api/tasks/e2e-mock-task", handle_task_status)

    def _navigate_to_generate(self, page, base_url):
        """导航到 Generate 页面并等待完成状态"""
        self._setup_route_mocks(page, base_url)
        page.goto(f"{base_url}/generate/e2e-mock-task", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    def _click_evaluate_button(self, page):
        """点击评估按钮（GraduationCap 图标按钮）"""
        # 评估按钮在 .card-toolbar 中，包含 svg 图标，tooltip "质量评估"
        eval_btn = page.locator('.card-toolbar button:has(svg)').last
        eval_btn.wait_for(state="visible", timeout=10000)
        eval_btn.click()
        page.wait_for_timeout(1000)

    def test_quality_dialog_renders(self, page, base_url, take_screenshot):
        """真实 QualityDialog 渲染等级、评分、维度、统计、优缺点、建议"""
        self._navigate_to_generate(page, base_url)
        take_screenshot("tc14_generate_page")

        self._click_evaluate_button(page)

        # 等待 dialog 出现
        dialog = page.locator('[role="dialog"]')
        dialog.wait_for(state="visible", timeout=10000)
        take_screenshot("tc14_quality_dialog_real")

        text = dialog.inner_text()

        # 等级 Badge
        assert "A-" in text, f"未找到等级 A-，内容: {text[:300]}"
        # 总分
        assert "83" in text, f"未找到总分 83，内容: {text[:300]}"
        # 6 维度标签
        for label in ["事实准确", "内容完整", "逻辑连贯", "主题相关", "引用质量", "写作质量"]:
            assert label in text, f"缺少评分维度: {label}"
        # 统计信息
        assert "3,500" in text or "3500" in text, "未找到字数统计"
        # 优缺点
        assert "代码示例丰富" in text, "未找到优点"
        assert "引用来源偏少" in text, "未找到不足"
        # 建议
        assert "补充" in text and "引用" in text, "未找到建议"
        # 总结
        assert "文章结构清晰" in text, "未找到总结"

    def test_quality_dialog_closes_esc(self, page, base_url, take_screenshot):
        """按 ESC 关闭对话框"""
        self._navigate_to_generate(page, base_url)
        self._click_evaluate_button(page)

        dialog = page.locator('[role="dialog"]')
        dialog.wait_for(state="visible", timeout=10000)

        # 按 ESC 关闭
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        take_screenshot("tc14_dialog_closed_esc")

        assert not dialog.is_visible(), "按 ESC 后对话框未关闭"

    def test_quality_dialog_closes_overlay(self, page, base_url, take_screenshot):
        """点击 dialog 外部关闭对话框"""
        self._navigate_to_generate(page, base_url)
        self._click_evaluate_button(page)

        dialog = page.locator('[role="dialog"]')
        dialog.wait_for(state="visible", timeout=10000)

        # 点击 dialog 外部（overlay 区域）
        page.mouse.click(10, 10)
        page.wait_for_timeout(500)
        take_screenshot("tc14_dialog_closed_overlay")

        assert not dialog.is_visible(), "点击外部后对话框未关闭"
