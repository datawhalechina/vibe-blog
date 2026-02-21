"""
TC-2: 博客生成主流程（P0 — 最关键）

完整模拟人操作：
  输入主题 → 展开高级选项 → 选择 mini → 点击生成 → 捕获 task_id
  → 进度抽屉 → SSE 监控（大纲/章节/完成）→ 跳转详情页
  → 验证详情页内容（标题/章节/正文/图片/代码块）
  → 后端数据校验 → 特性验证 → 控制台错误检查
"""
from e2e_utils import (
    find_element,
    fill_input,
    clear_input,
    INPUT_SELECTORS,
    GENERATE_BTN_SELECTORS,
    get_blog_detail_api,
    get_task_status,
    run_feature_checks,
)


class TestBlogGeneration:
    """博客生成端到端测试"""

    def test_full_generation_mini(
        self, page, base_url, take_screenshot, console_logs, save_logs
    ):
        """Mini 模式完整生成流程 — 真实 LLM 调用，非 mock"""

        topic = "Python 列表推导式入门"

        # ── Step 1: 打开首页 ──
        page.goto(base_url, wait_until="networkidle")
        take_screenshot("01_home_loaded")

        # ── Step 2: 输入主题 ──
        input_el, used_selector = find_element(page, INPUT_SELECTORS)
        assert input_el is not None, f"未找到主题输入框，尝试过: {INPUT_SELECTORS}"
        fill_input(page, input_el, topic)
        take_screenshot("02_topic_filled")

        # ── Step 3: 展开高级选项，选择 mini ──
        adv_btn = page.locator("button.code-action-btn:has-text('高级选项')")
        adv_btn.click()
        page.wait_for_timeout(500)
        length_select = page.locator("select").nth(1)
        length_select.select_option("mini")
        take_screenshot("03_mini_selected")

        # ── Step 4: 点击生成，捕获 task_id ──
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
        take_screenshot("04_generate_clicked")

        assert captured_task_id, "未捕获到 task_id"

        # ── Step 5: 等待进度抽屉出现 ──
        page.locator(".progress-drawer").wait_for(state="visible", timeout=15000)
        take_screenshot("05_progress_drawer")

        # ── Step 6: SSE 监控 — 等待生成完成 ──
        max_wait = 600  # 10 分钟
        poll_interval = 5
        waited = 0
        last_section_count = 0

        while waited < max_wait:
            done = page.evaluate("() => window.__sse_generation_done")
            if done:
                break

            if '/blog/' in page.url and page.url != base_url:
                break

            # 记录进度：每收到新 section 截图一次
            section_count = page.evaluate("() => (window.__sse_sections || []).length")
            if section_count > last_section_count:
                take_screenshot(f"06_section_{section_count}")
                last_section_count = section_count

            if waited % 60 == 0 and waited > 0:
                take_screenshot(f"06_wait_{waited}s")

            page.wait_for_timeout(poll_interval * 1000)
            waited += poll_interval

        take_screenshot("07_generation_done")

        # ── Step 7: 验证生成完成 ──
        page.wait_for_timeout(5000)
        # 生成完成后可能停留在 /generate/ 或跳转到 /blog/
        current_url = page.url
        if '/blog/' in current_url:
            blog_id = current_url.rstrip('/').split('/')[-1]
        else:
            # 停留在 /generate/task_xxx，用 task_id 作为 blog_id
            blog_id = captured_task_id

        # 导航到详情页验证内容
        page.goto(f"{base_url}/blog/{blog_id}", wait_until="networkidle")
        page.wait_for_load_state("networkidle", timeout=15000)
        take_screenshot("08_detail_page")

        # ── Step 8: 验证详情页核心内容 ──
        # 标题可见且非空
        blog_title = page.locator(".blog-title")
        blog_title.wait_for(state="visible", timeout=10000)
        title_text = blog_title.text_content()
        assert title_text and title_text.strip(), "博客标题为空"

        # 正文可见且长度 > 100
        blog_content = page.locator(".blog-content")
        blog_content.wait_for(state="visible", timeout=10000)
        content_text = blog_content.text_content()
        assert content_text and len(content_text) > 100, \
            f"正文内容过短: {len(content_text or '')} 字符"

        # 至少 1 个章节标题
        h2_count = page.locator(".blog-content h2").count()
        assert h2_count >= 1, f"未找到章节标题 h2，数量: {h2_count}"

        take_screenshot("09_content_verified")

        # ── Step 9: 验证 SSE 捕获的数据 ──
        outline = page.evaluate("() => window.__sse_outline_data")
        sections = page.evaluate("() => window.__sse_sections || []")
        assert len(sections) >= 1 or outline is not None, \
            "SSE hook 未捕获到 outline 或 sections"

        # ── Step 10: 后端数据校验 ──
        blog_data = get_blog_detail_api(blog_id)
        if blog_data:
            # 验证后端确实存储了生成结果
            assert blog_data.get("success", True), \
                f"后端返回失败: {blog_data}"

        # ── Step 11: 任务状态校验 ──
        task_info = get_task_status(captured_task_id)
        if task_info:
            assert task_info.get("status") in ("completed", "done", "success"), \
                f"任务状态异常: {task_info.get('status')}"

        # ── Step 12: 特性验证（迁移新特性检查）──
        feature_results = run_feature_checks(page, blog_data)
        failed_features = [r for r in feature_results if not r["passed"]]
        if failed_features:
            msgs = [f"{r['feature']}: {r['message']}" for r in failed_features]
            assert False, f"特性验证失败: {msgs}"

        # ── Step 13: 控制台错误检查 ──
        console_errors = [
            log for log in console_logs
            if log["type"] == "error"
            and "favicon" not in log["text"].lower()
        ]
        if console_errors:
            error_texts = [e["text"][:200] for e in console_errors[:5]]
            assert False, f"浏览器控制台有 {len(console_errors)} 个错误: {error_texts}"

        take_screenshot("10_all_passed")

    def test_generate_button_state(self, page, base_url):
        """生成按钮在输入主题前后的状态变化"""
        page.goto(base_url, wait_until="networkidle")

        gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
        assert gen_btn is not None, "未找到生成按钮"
        assert gen_btn.is_disabled(), "空主题时按钮应 disabled"

        input_el, _ = find_element(page, INPUT_SELECTORS)
        assert input_el is not None, "未找到主题输入框"
        fill_input(page, input_el, "测试主题")
        assert gen_btn.is_enabled(), "有主题时按钮应 enabled"

        clear_input(page, input_el)
        assert gen_btn.is_disabled(), "清空后按钮应 disabled"
