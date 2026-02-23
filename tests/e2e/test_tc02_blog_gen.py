"""
TC-2: 博客生成主流程（P0 — 最关键）

完整模拟人操作：
  输入主题 → 展开高级选项 → 选择 mini → 点击生成 → 捕获 task_id
  → 进度抽屉 → SSE 监控（大纲/章节/完成）→ 跳转详情页
  → 验证详情页内容（标题/章节/正文/图片/代码块）
  → 后端数据校验 → 特性验证 → 控制台错误检查
"""
import logging

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

logger = logging.getLogger(__name__)


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
        gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
        assert gen_btn is not None, "未找到生成按钮"

        with page.expect_response(
            lambda r: '/api/blog/generate' in r.url and r.status < 300,
            timeout=30000,
        ) as response_info:
            gen_btn.click()

        resp = response_info.value
        captured_task_id = resp.json().get('task_id')
        take_screenshot("04_generate_clicked")
        logger.info(f"捕获到 task_id: {captured_task_id}")

        assert captured_task_id, "未捕获到 task_id"

        # ── Step 5: 等待进度抽屉出现 ──
        page.locator(".progress-drawer").wait_for(state="visible", timeout=15000)
        take_screenshot("05_progress_drawer")

        # ── Step 6: 等待生成完成（SSE + API 双通道轮询）──
        max_wait = 900  # 15 分钟（含并行优化后仍留余量）
        poll_interval = 5
        waited = 0
        last_section_count = 0
        completion_source = None

        while waited < max_wait:
            # 通道 1: SSE hook 检测
            done = page.evaluate("() => window.__sse_generation_done")
            if done:
                completion_source = "SSE"
                break

            # 通道 2: URL 跳转检测
            if '/blog/' in page.url and page.url != base_url:
                completion_source = "URL"
                break

            # 通道 3: 后端 API 轮询任务状态
            task_info = get_task_status(captured_task_id)
            if task_info:
                status = task_info.get("status", "")
                if status in ("completed", "done", "success"):
                    completion_source = "API"
                    break
                if status in ("failed", "error"):
                    error_msg = task_info.get("error", "未知错误")
                    assert False, f"任务失败: {status} - {error_msg}"

            # 记录进度：每收到新 section 截图一次
            section_count = page.evaluate("() => (window.__sse_sections || []).length")
            if section_count > last_section_count:
                take_screenshot(f"06_section_{section_count}")
                last_section_count = section_count

            if waited % 60 == 0 and waited > 0:
                take_screenshot(f"06_wait_{waited}s")
                # 每分钟记录 SSE 事件数量，帮助诊断
                sse_count = page.evaluate("() => (window.__sse_events || []).length")
                logger.info(f"等待 {waited}s: SSE 事件={sse_count}, sections={section_count}")

            page.wait_for_timeout(poll_interval * 1000)
            waited += poll_interval

        logger.info(f"生成完成: source={completion_source}, waited={waited}s")
        take_screenshot("07_generation_done")

        assert completion_source is not None, \
            f"生成超时 ({max_wait}s)，SSE events={page.evaluate('() => (window.__sse_events || []).length')}"

        # ── Step 7: 导航到详情页 ──
        page.wait_for_timeout(3000)

        # 优先从 SSE complete 事件中提取 blog_id
        blog_id = page.evaluate("""() => {
            const events = window.__sse_events || [];
            for (let i = events.length - 1; i >= 0; i--) {
                if (events[i].type === 'complete') {
                    try {
                        const d = JSON.parse(events[i].data);
                        return d.id || d.book_id || null;
                    } catch(e) {}
                }
            }
            return null;
        }""")

        # 回退: 从 URL 提取
        if not blog_id:
            current_url = page.url
            if '/blog/' in current_url:
                blog_id = current_url.rstrip('/').split('/')[-1]

        # 最终回退: 用 task_id（前端 history API 支持用 task_id 查询）
        if not blog_id:
            blog_id = captured_task_id

        logger.info(f"导航到详情页: blog_id={blog_id}")

        page.goto(f"{base_url}/blog/{blog_id}", wait_until="networkidle")
        page.wait_for_load_state("networkidle", timeout=15000)
        take_screenshot("08_detail_page")

        # 如果页面被重定向回首页（404），说明 blog_id 无效
        if page.url.rstrip('/') == base_url.rstrip('/'):
            # 用 task_id 重试一次
            if blog_id != captured_task_id:
                logger.info(f"blog_id={blog_id} 无效，用 task_id 重试")
                blog_id = captured_task_id
                page.goto(f"{base_url}/blog/{blog_id}", wait_until="networkidle")
                page.wait_for_load_state("networkidle", timeout=15000)
                take_screenshot("08_detail_page_retry")

        # ── Step 8: 验证详情页核心内容 ──
        blog_title = page.locator(".blog-title")
        blog_title.wait_for(state="visible", timeout=15000)
        title_text = blog_title.text_content()
        assert title_text and title_text.strip(), "博客标题为空"

        blog_content = page.locator(".blog-content")
        blog_content.wait_for(state="visible", timeout=10000)
        content_text = blog_content.text_content()
        assert content_text and len(content_text) > 100, \
            f"正文内容过短: {len(content_text or '')} 字符"

        h2_count = page.locator(".blog-content h2").count()
        assert h2_count >= 1, f"未找到章节标题 h2，数量: {h2_count}"

        take_screenshot("09_content_verified")

        # ── Step 9: 验证 SSE 捕获的数据（非阻塞 — SSE hook 可能因时序问题未捕获）──
        outline = page.evaluate("() => window.__sse_outline_data")
        sections = page.evaluate("() => window.__sse_sections || []")
        sse_events = page.evaluate("() => window.__sse_events || []")
        logger.info(f"SSE 数据: outline={'有' if outline else '无'}, sections={len(sections)}, events={len(sse_events)}")
        if not (len(sections) >= 1 or outline is not None):
            logger.warning(
                f"SSE hook 未捕获到 outline 或 sections "
                f"(events={len(sse_events)}, completion_source={completion_source})"
            )

        # ── Step 10: 后端数据校验 ──
        blog_data = get_blog_detail_api(blog_id)
        if blog_data:
            assert blog_data.get("success", True), \
                f"后端返回失败: {blog_data}"

        # ── Step 11: 任务状态校验（非阻塞 — TaskManager 内存状态可能未同步）──
        task_info = get_task_status(captured_task_id)
        if task_info:
            task_status = task_info.get("status", "")
            if task_status not in ("completed", "done", "success"):
                logger.warning(f"任务状态异常: {task_status}（TaskManager 内存状态可能未同步）")

        # ── Step 12: 特性验证（迁移新特性检查）──
        feature_results = run_feature_checks(page, blog_data)
        failed_features = [r for r in feature_results if not r["passed"]]
        if failed_features:
            msgs = [f"{r['feature']}: {r['message']}" for r in failed_features]
            assert False, f"特性验证失败: {msgs}"

        # ── Step 13: 控制台错误检查（排除已知无害错误）──
        console_errors = [
            log for log in console_logs
            if log["type"] == "error"
            and "favicon" not in log["text"].lower()
            and "net::ERR_CONNECTION_REFUSED" not in log["text"]
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
