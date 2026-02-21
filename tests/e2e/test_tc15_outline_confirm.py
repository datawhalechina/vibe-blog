"""
TC-15: 大纲确认交互测试

验证真实的大纲确认流程：
  输入主题 → 点击生成 → 等待大纲到达 → 大纲确认 Card 出现
  → 验证章节列表 → 点击"开始写作" → Card 消失 → 写作继续

注意：此测试需要真实后端运行，大纲确认通过 POST /api/tasks/{taskId}/resume 通知后端。
"""
from e2e_utils import (
    find_element,
    fill_input,
    cancel_task,
    INPUT_SELECTORS,
    GENERATE_BTN_SELECTORS,
    FRONTEND_URL,
)


class TestOutlineConfirm:
    """大纲确认交互测试"""

    def test_outline_confirm_flow(self, page, base_url, take_screenshot):
        """完整大纲确认流程：等待大纲 → 验证内容 → 点击开始写作 → 写作继续"""

        topic = "Python 装饰器详解"
        captured_task_id = None

        # ── Step 1: 打开首页，输入主题 ──
        page.goto(base_url, wait_until="networkidle")

        input_el, _ = find_element(page, INPUT_SELECTORS)
        assert input_el is not None, f"未找到主题输入框，尝试过: {INPUT_SELECTORS}"
        fill_input(page, input_el, topic)
        take_screenshot("tc15_01_topic_filled")

        # ── Step 2: 点击生成，捕获 task_id ──
        def on_response(response):
            nonlocal captured_task_id
            if '/api/blog/generate' in response.url and response.status < 300:
                try:
                    body = response.json()
                    captured_task_id = body.get('task_id')
                except Exception:
                    pass

        page.on('response', on_response)

        gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
        assert gen_btn is not None, "未找到生成按钮"
        gen_btn.click()
        page.wait_for_timeout(3000)
        take_screenshot("tc15_02_generate_clicked")

        assert captured_task_id, "未捕获到 task_id"

        try:
            # ── Step 3: 轮询等待大纲到达 ──
            max_wait = 180  # 3 分钟
            poll_interval = 3
            waited = 0
            outline_data = None

            while waited < max_wait:
                outline_data = page.evaluate("() => window.__sse_outline_data")
                if outline_data:
                    break
                page.wait_for_timeout(poll_interval * 1000)
                waited += poll_interval

            assert outline_data is not None, \
                f"超时 {max_wait}s：未收到 outline_complete 事件"
            take_screenshot("tc15_03_outline_received")

            # ── Step 4: 等待大纲确认 Card 出现 ──
            confirm_btn = page.locator('button:has-text("开始写作")')
            confirm_btn.wait_for(state="visible", timeout=15000)
            take_screenshot("tc15_04_outline_card")

            # ── Step 5: 验证大纲内容 — Card 内 li 元素 ──
            # 大纲 Card 是包含"开始写作"按钮的最近父级 Card
            outline_card = confirm_btn.locator("xpath=ancestor::*[contains(@class,'card') or contains(@class,'Card')]").first
            li_elements = outline_card.locator("li")
            li_count = li_elements.count()
            assert li_count >= 1, f"大纲章节列表为空，li 数量: {li_count}"
            take_screenshot("tc15_05_outline_content")

            # 验证"修改大纲"按钮也存在
            edit_btn = page.locator('button:has-text("修改大纲")')
            assert edit_btn.is_visible(), "未找到'修改大纲'按钮"

            # ── Step 6: 点击"开始写作" ──
            confirm_btn.click()
            take_screenshot("tc15_06_confirm_clicked")

            # ── Step 7: 等待大纲确认 Card 消失 ──
            confirm_btn.wait_for(state="hidden", timeout=10000)
            take_screenshot("tc15_07_card_dismissed")

            # ── Step 8: 验证写作继续 — 新的 progress-log-item 出现 ──
            page.locator(".progress-log-item").last.wait_for(
                state="visible", timeout=30000
            )
            take_screenshot("tc15_08_writing_continues")

        finally:
            # ── Step 9: 取消任务清理 ──
            cancel_task(captured_task_id)
