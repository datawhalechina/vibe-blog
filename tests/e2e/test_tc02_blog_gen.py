"""
TC-2: 博客生成主流程（P0 — 最关键）

完整流程：输入主题 → 点击生成 → 捕获 task_id → 进度抽屉 → SSE 监控 → 跳转详情页 → 验证内容
含 mini 模式变体（CI 友好）
"""
from e2e_utils import find_element, INPUT_SELECTORS, GENERATE_BTN_SELECTORS


class TestBlogGeneration:
    """博客生成端到端测试"""

    def test_full_generation_mini(self, page, base_url, take_screenshot):
        """Mini 模式生成（CI 友好，耗时较短）"""
        page.goto(base_url, wait_until="networkidle")
        take_screenshot("01_home")

        # 输入主题
        input_el, _ = find_element(page, INPUT_SELECTORS)
        assert input_el is not None, "未找到主题输入框"
        input_el.click()
        input_el.fill("Python 列表推导式入门")

        # 展开高级选项，选择 mini
        adv_btn = page.locator("button.code-action-btn:has-text('高级选项')")
        adv_btn.click()
        page.wait_for_timeout(500)
        length_select = page.locator("select").nth(1)
        length_select.select_option("mini")
        take_screenshot("02_mini_selected")

        # 点击生成，捕获 task_id
        captured_task_id = None

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
        take_screenshot("03_clicked")

        assert captured_task_id, "未捕获到 task_id"

        # 等待进度抽屉出现
        page.locator(".progress-drawer").wait_for(state="visible", timeout=15000)
        take_screenshot("04_progress")

        # SSE 监控：等待 generation_complete 或 URL 跳转
        max_wait = 600  # 10 分钟
        poll_interval = 5
        waited = 0

        while waited < max_wait:
            # 检查 SSE hook 的 generation_complete
            done = page.evaluate("() => window.__sse_generation_done")
            if done:
                break

            # 检查 URL 跳转到 /blog/:id
            if '/blog/' in page.url and page.url != base_url:
                break

            if waited % 60 == 0 and waited > 0:
                take_screenshot(f"05_wait_{waited}s")

            page.wait_for_timeout(poll_interval * 1000)
            waited += poll_interval

        take_screenshot("06_done")

        # 等待前端自动跳转（complete 事件后 1s）
        page.wait_for_timeout(5000)
        assert '/blog/' in page.url, f"未跳转到详情页，当前 URL: {page.url}"

        # 验证详情页内容
        page.wait_for_load_state("networkidle", timeout=15000)
        take_screenshot("07_detail")

        # 验证 SSE 捕获的数据
        outline = page.evaluate("() => window.__sse_outline_data")
        sections = page.evaluate("() => window.__sse_sections || []")
        assert len(sections) >= 1 or outline is not None, \
            "SSE hook 未捕获到 outline 或 sections"

    def test_generate_button_state(self, page, base_url):
        """生成按钮在输入主题前后的状态变化"""
        page.goto(base_url, wait_until="networkidle")

        gen_btn = page.locator("button.code-generate-btn")
        assert gen_btn.is_disabled(), "空主题时按钮应 disabled"

        textarea = page.locator("textarea.code-input-textarea")
        textarea.fill("测试主题")
        assert gen_btn.is_enabled(), "有主题时按钮应 enabled"

        textarea.fill("")
        assert gen_btn.is_disabled(), "清空后按钮应 disabled"
