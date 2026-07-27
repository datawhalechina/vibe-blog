"""
TC-12: 错误处理（P2）

验证：空主题/纯空格时生成按钮 disabled
"""
from e2e_utils import (
    find_element,
    fill_input,
    GENERATE_BTN_SELECTORS,
    INPUT_SELECTORS,
)


def test_empty_topic_disabled(page, base_url):
    """空主题时生成按钮 disabled"""
    page.goto(base_url, wait_until="networkidle")
    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    assert gen_btn is not None
    assert gen_btn.is_disabled()


def test_whitespace_topic_disabled(page, base_url):
    """纯空格主题时生成按钮 disabled"""
    page.goto(base_url, wait_until="networkidle")
    input_el, _ = find_element(page, INPUT_SELECTORS)
    assert input_el is not None
    fill_input(page, input_el, "   ")
    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    assert gen_btn is not None
    assert gen_btn.is_disabled()
