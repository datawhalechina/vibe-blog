"""
TC-8: 暗黑模式切换（P2）

验证：主题切换按钮工作，dark-mode class 变化
"""


def test_theme_toggle(page, base_url, take_screenshot):
    """切换暗黑/浅色主题"""
    page.goto(base_url, wait_until="networkidle")
    take_screenshot("theme_initial")

    toggle = page.locator("button.theme-toggle")
    assert toggle.is_visible()

    # 记录初始状态
    has_dark = page.locator(".dark-mode").count() > 0

    # 切换
    toggle.click()
    page.wait_for_timeout(500)
    take_screenshot("theme_toggled")

    has_dark_after = page.locator(".dark-mode").count() > 0
    assert has_dark != has_dark_after, "主题切换后 dark-mode 状态应变化"

    # 切回
    toggle.click()
    page.wait_for_timeout(500)
    has_dark_restored = page.locator(".dark-mode").count() > 0
    assert has_dark == has_dark_restored, "再次切换应恢复原状态"
