"""
TC-11: 响应式布局（P2）

验证：移动端视口下关键元素可见性
"""


def test_mobile_layout(browser, base_url):
    """375×812 移动端视口布局正常"""
    ctx = browser.new_context(
        viewport={"width": 375, "height": 812},
        locale="zh-CN",
    )
    p = ctx.new_page()
    p.goto(base_url, wait_until="networkidle")

    # 输入卡片应可见
    assert p.locator("textarea.code-input-textarea").is_visible()

    # 生成按钮应可见
    assert p.locator("button.code-generate-btn").is_visible()

    p.close()
    ctx.close()


def test_tablet_layout(browser, base_url):
    """1024×768 平板视口布局正常"""
    ctx = browser.new_context(
        viewport={"width": 1024, "height": 768},
        locale="zh-CN",
    )
    p = ctx.new_page()
    p.goto(base_url, wait_until="networkidle")

    assert p.locator("textarea.code-input-textarea").is_visible()
    assert p.locator("button.code-generate-btn").is_visible()

    p.close()
    ctx.close()
