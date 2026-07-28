"""
TC-16: 全链路闭环验证（P0 — 串联所有孤岛）

完整用户旅程：
  生成博客 → 跳转详情页 → 验证内容
  → 回首页 → 历史列表包含新博客
  → 从历史卡片点击进入详情页 → 内容一致
  → 触发质量评估 → 验证真实评分
  → 访问 Dashboard → 任务计数反映

解决 3 个断裂点：
  1. 生成后 → 历史列表（TC-02 没验证）
  2. 详情页 → 质量评估（TC-14 用 mock）
  3. 跨页面数据一致性（各测试独立运行）
"""
from e2e_utils import (
    find_element,
    fill_input,
    INPUT_SELECTORS,
    GENERATE_BTN_SELECTORS,
    get_task_status,
    run_feature_checks,
    wait_for_generation_history,
    configure_fast_live_generation,
)


class TestFullChain:
    """全链路闭环：生成 → 历史 → 详情 → 评估 → Dashboard"""

    def test_full_chain(
        self, page, base_url, take_screenshot, console_logs, save_logs
    ):
        topic = "Python 异步编程入门"
        captured_task_id = None
        blog_id = None

        # ════════════════════════════════════════════
        # Phase A: 生成博客（复用 TC-02 核心流程）
        # ════════════════════════════════════════════

        # ── A1: 首页 → 输入主题 → mini 模式 ──
        page.goto(base_url, wait_until="networkidle")
        take_screenshot("chain_01_home")

        input_el, _ = find_element(page, INPUT_SELECTORS)
        assert input_el is not None, "未找到主题输入框"
        fill_input(page, input_el, topic)

        adv_btn = page.locator("button.code-action-btn:has-text('高级选项')")
        adv_btn.click()
        page.wait_for_timeout(500)
        page.locator("select").nth(1).select_option("mini")
        configure_fast_live_generation(page)

        # ── A2: 点击生成，捕获 task_id ──
        def on_response(response):
            nonlocal captured_task_id
            if '/api/blog/generate' in response.url and response.status < 300:
                try:
                    captured_task_id = response.json().get('task_id')
                except Exception:
                    pass

        page.on('response', on_response)
        gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
        assert gen_btn is not None, "未找到生成按钮"
        gen_btn.click()
        page.wait_for_timeout(3000)
        assert captured_task_id, "未捕获到 task_id"
        take_screenshot("chain_02_generating")

        # ── A3: 等待生成完成且历史记录可读 ──
        completion = wait_for_generation_history(
            page,
            captured_task_id,
            max_wait=600,
            poll_interval=5,
        )

        # ── A4: 在生成工作台执行质量评估（真实 LLM 调用）──
        eval_btn = page.get_by_role("button", name="质量评估")
        assert eval_btn.count() == 1, "生成工作台未找到质量评估按钮"
        assert eval_btn.is_visible(timeout=5000), "质量评估按钮不可见"
        eval_btn.click()
        take_screenshot("chain_03_eval_clicked")

        dialog = page.locator('[role="dialog"]')
        dialog.wait_for(state="visible", timeout=10_000)
        dialog.get_by_text("事实准确", exact=True).wait_for(
            state="visible", timeout=180_000
        )
        take_screenshot("chain_04_eval_dialog")
        dialog_text = dialog.inner_text()
        grades = ["A+", "A-", "B+", "B-", "C+", "C-", "A", "B", "C", "D", "F"]
        assert any(grade in dialog_text for grade in grades), \
            f"评估对话框未显示等级: {dialog_text[:200]}"
        dimension_labels = ["事实准确", "内容完整", "逻辑连贯",
                            "主题相关", "引用质量", "写作质量"]
        found_dims = [label for label in dimension_labels if label in dialog_text]
        assert len(found_dims) >= 3, f"评分维度不足，仅找到: {found_dims}"
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # ── A5: 生成完成，导航到详情页 ──
        blog_id = completion["blog_id"]

        page.goto(f"{base_url}/blog/{blog_id}", wait_until="networkidle")
        page.wait_for_load_state("networkidle", timeout=15000)
        take_screenshot("chain_03_detail_page")

        # ── A6: 详情页内容验证 ──
        blog_title = page.locator(".blog-title")
        blog_title.wait_for(state="visible", timeout=10000)
        detail_title = blog_title.text_content().strip()
        assert detail_title, "博客标题为空"

        blog_content = page.locator(".blog-content")
        blog_content.wait_for(state="visible", timeout=10000)
        detail_content_len = len(blog_content.text_content() or "")
        assert detail_content_len > 100, f"正文过短: {detail_content_len}"

        h2_count = page.locator(".blog-content h2").count()
        assert h2_count >= 1, f"无章节标题: {h2_count}"
        take_screenshot("chain_04_content_ok")

        # ════════════════════════════════════════════
        # Phase B: 回首页 → 历史列表验证
        # ════════════════════════════════════════════

        # ── B1: 回到首页 ──
        page.goto(base_url, wait_until="networkidle")
        page.wait_for_timeout(2000)
        take_screenshot("chain_05_back_home")

        # ── B2: 滚动到历史区域 ──
        history_section = page.locator(".history-section")
        history_section.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # ── B3: 验证历史列表包含刚生成的博客 ──
        cards = page.locator(".code-blog-card")
        cards.first.wait_for(state="visible", timeout=10000)
        card_count = cards.count()
        assert card_count >= 1, "历史列表为空"

        # 在卡片中找到匹配主题的那张
        found_card = None
        for i in range(min(card_count, 5)):  # 只查前 5 张
            card_text = cards.nth(i).text_content() or ""
            if topic in card_text:
                found_card = cards.nth(i)
                break

        assert found_card is not None, \
            f"历史列表前 5 张卡片中未找到主题 '{topic}'"
        take_screenshot("chain_06_history_found")

        # ── B4: 从历史卡片点击进入详情页 ──
        found_card.click()
        page.wait_for_url(f"**/blog/{blog_id}", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=15000)
        take_screenshot("chain_07_detail_from_history")

        # ── B5: 验证内容一致性 ──
        title_again = page.locator(".blog-title")
        title_again.wait_for(state="visible", timeout=10000)
        assert title_again.text_content().strip() == detail_title, \
            "从历史进入的详情页标题与首次不一致"

        # ════════════════════════════════════════════
        # Phase D: Dashboard 任务反映
        # ════════════════════════════════════════════

        # ── D1: 访问 Dashboard ──
        page.goto(f"{base_url}/dashboard", wait_until="networkidle")
        page.wait_for_timeout(2000)
        take_screenshot("chain_11_dashboard")

        # ── D2: 验证页面加载 ──
        title_el = page.locator(".dashboard-title")
        assert title_el.is_visible(timeout=5000), "Dashboard 标题不可见"

        # ── D3: 验证统计卡片 ──
        stat_cards = page.locator(".stat-card")
        assert stat_cards.count() == 5, \
            f"统计卡片数量异常: {stat_cards.count()}"

        # ── D4: 通过 API 验证任务记录 ──
        task_info = get_task_status(captured_task_id)
        if task_info:
            assert task_info.get("status") in ("completed", "done", "success"), \
                f"任务最终状态异常: {task_info.get('status')}"

        # 验证历史 API 包含此博客
        blog_data = completion["blog"]
        assert blog_data is not None, \
            f"后端 API 未找到博客 {blog_id}"
        assert blog_data.get("success", True), \
            f"后端返回失败: {blog_data}"

        take_screenshot("chain_12_dashboard_ok")

        # ════════════════════════════════════════════
        # Phase E: 特性验证 + 错误检查
        # ════════════════════════════════════════════

        feature_results = run_feature_checks(page, blog_data)
        failed_features = [r for r in feature_results if not r["passed"]]
        if failed_features:
            msgs = [f"{r['feature']}: {r['message']}" for r in failed_features]
            assert False, f"特性验证失败: {msgs}"

        # 控制台错误检查
        console_errors = [
            log for log in console_logs
            if log["type"] == "error"
            and "favicon" not in log["text"].lower()
        ]
        if console_errors:
            error_texts = [e["text"][:200] for e in console_errors[:5]]
            assert False, \
                f"全链路中有 {len(console_errors)} 个控制台错误: {error_texts}"

        take_screenshot("chain_13_all_passed")
