"""
TC-3: 高级选项面板（P1）

验证：面板展开/收起、各 select 交互、custom 长度额外配置
"""


def test_advanced_options_toggle(page, base_url, take_screenshot):
    """高级选项面板展开和收起"""
    page.goto(base_url, wait_until="networkidle")

    adv_btn = page.locator("button.code-action-btn:has-text('高级选项')")
    assert adv_btn.is_visible()

    # 点击展开
    adv_btn.click()
    page.wait_for_timeout(500)
    take_screenshot("advanced_open")

    # 应有多个 select 元素（文章类型、长度、受众、配图风格）
    selects = page.locator("select").all()
    assert len(selects) >= 3, f"期望至少 3 个 select，实际 {len(selects)}"

    # 点击收起
    adv_btn.click()
    page.wait_for_timeout(500)
    take_screenshot("advanced_closed")


def test_select_article_type(page, base_url, take_screenshot):
    """切换文章类型"""
    page.goto(base_url, wait_until="networkidle")

    page.locator("button.code-action-btn:has-text('高级选项')").click()
    page.wait_for_timeout(500)

    # 第一个 select 是文章类型
    type_select = page.locator("select").first
    type_select.select_option("comparison")
    take_screenshot("type_comparison")

    type_select.select_option("tutorial")
    take_screenshot("type_tutorial")


def test_select_length_mini(page, base_url, take_screenshot):
    """选择 mini 长度"""
    page.goto(base_url, wait_until="networkidle")

    page.locator("button.code-action-btn:has-text('高级选项')").click()
    page.wait_for_timeout(500)

    length_select = page.locator("select").nth(1)
    length_select.select_option("mini")
    take_screenshot("length_mini")


def test_custom_length_shows_config(page, base_url, take_screenshot):
    """选择 custom 长度显示额外配置"""
    page.goto(base_url, wait_until="networkidle")

    page.locator("button.code-action-btn:has-text('高级选项')").click()
    page.wait_for_timeout(500)

    length_select = page.locator("select").nth(1)
    length_select.select_option("custom")
    page.wait_for_timeout(300)
    take_screenshot("custom_config")

    # custom 模式下应出现数字输入框
    number_inputs = page.locator("input[type='number']")
    assert number_inputs.count() >= 2, "custom 模式应显示数字配置输入框"
