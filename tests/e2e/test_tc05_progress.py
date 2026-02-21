"""
TC-5: 进度抽屉 & SSE 监控（P1）

验证：进度抽屉出现、日志条目增长、状态徽章、展开/收起
"""
from e2e_utils import find_element, fill_input, INPUT_SELECTORS, GENERATE_BTN_SELECTORS, cancel_task


def test_progress_drawer_appears(page, base_url, take_screenshot):
    """点击生成后进度抽屉出现"""
    page.goto(base_url, wait_until="networkidle")

    input_el, _ = find_element(page, INPUT_SELECTORS)
    fill_input(page, input_el, "E2E 进度测试")

    captured_task_id = None

    def on_response(resp):
        nonlocal captured_task_id
        if '/api/blog/generate' in resp.url and resp.status < 300:
            try:
                captured_task_id = resp.json().get('task_id')
            except Exception:
                pass

    page.on('response', on_response)

    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    gen_btn.click()

    # 进度抽屉应出现
    drawer = page.locator(".progress-drawer")
    drawer.wait_for(state="visible", timeout=15000)
    take_screenshot("drawer_visible")

    # 等待日志条目出现
    page.wait_for_timeout(10000)
    log_items = page.locator(".progress-log-item")
    assert log_items.count() >= 1, "应有至少 1 条进度日志"
    take_screenshot("logs_appeared")

    # 清理
    if captured_task_id:
        cancel_task(captured_task_id)
