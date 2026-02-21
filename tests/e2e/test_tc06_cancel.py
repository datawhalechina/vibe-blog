"""
TC-6: 任务取消（P1）

验证：点击停止按钮中断生成
"""
from e2e_utils import find_element, fill_input, INPUT_SELECTORS, GENERATE_BTN_SELECTORS


def test_cancel_generation(page, base_url, take_screenshot):
    """点击停止按钮取消正在进行的生成"""
    page.goto(base_url, wait_until="networkidle")

    input_el, _ = find_element(page, INPUT_SELECTORS)
    fill_input(page, input_el, "取消测试主题")

    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    gen_btn.click()

    # 等待进度抽屉
    page.locator(".progress-drawer").wait_for(state="visible", timeout=15000)
    page.wait_for_timeout(3000)

    # 点击停止按钮
    stop_btn = page.locator("button.progress-stop-btn")
    if stop_btn.is_visible(timeout=5000):
        take_screenshot("before_cancel")
        stop_btn.click()
        page.wait_for_timeout(3000)
        take_screenshot("after_cancel")

        # 页面应留在首页（不跳转到 /blog/）
        assert '/blog/' not in page.url, "取消后不应跳转到详情页"
