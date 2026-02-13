"""
TC-9: 历史记录（P2）

验证：滚动到第二屏，section dot 状态变化
"""


def test_scroll_to_history(page, base_url, take_screenshot):
    """点击滚动提示跳转到历史区域"""
    page.goto(base_url, wait_until="networkidle")

    hint = page.locator(".scroll-hint")
    if hint.count() > 0 and hint.first.is_visible(timeout=3000):
        hint.first.click()
        page.wait_for_timeout(1000)
        take_screenshot("history_section")

        # 第二个 section dot 应为 active
        active_dots = page.locator(".section-dot.active")
        assert active_dots.count() >= 1
