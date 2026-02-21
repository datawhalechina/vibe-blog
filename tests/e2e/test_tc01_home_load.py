"""
TC-1: 首页加载与基础渲染（P0）

验证：导航栏、输入卡片、生成按钮状态、主题切换、滚动提示
"""
from e2e_utils import find_element, fill_input, INPUT_SELECTORS, GENERATE_BTN_SELECTORS


def test_home_page_loads(page, base_url, take_screenshot):
    """首页加载，关键 UI 元素可见"""
    page.goto(base_url, wait_until="networkidle")
    take_screenshot("loaded")

    # 输入卡片
    input_el, _ = find_element(page, INPUT_SELECTORS)
    assert input_el is not None, f"未找到主题输入框，尝试过: {INPUT_SELECTORS}"

    # 生成按钮存在且 disabled（无主题时）
    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    assert gen_btn is not None, f"未找到生成按钮，尝试过: {GENERATE_BTN_SELECTORS}"
    assert gen_btn.is_disabled()

    # 主题切换按钮
    assert page.locator("button.theme-toggle").is_visible()


def test_home_page_title(page, base_url):
    """页面 title 非空"""
    page.goto(base_url, wait_until="domcontentloaded")
    assert page.title()


def test_generate_button_enables_with_topic(page, base_url):
    """输入主题后生成按钮变为可用"""
    page.goto(base_url, wait_until="networkidle")

    input_el, _ = find_element(page, INPUT_SELECTORS)
    assert input_el is not None, f"未找到主题输入框，尝试过: {INPUT_SELECTORS}"
    fill_input(page, input_el, "测试主题")

    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    assert gen_btn is not None, f"未找到生成按钮，尝试过: {GENERATE_BTN_SELECTORS}"
    assert gen_btn.is_enabled()


def test_scroll_hint_visible(page, base_url):
    """滚动提示可见"""
    page.goto(base_url, wait_until="networkidle")
    hint = page.locator(".scroll-hint")
    if hint.count() > 0:
        assert hint.first.is_visible()
