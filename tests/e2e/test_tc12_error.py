"""
TC-12: 错误处理（P2）

验证：空主题/纯空格时生成按钮 disabled
"""
from e2e_utils import find_element, GENERATE_BTN_SELECTORS


def test_empty_topic_disabled(page, base_url):
    """空主题时生成按钮 disabled"""
    page.goto(base_url, wait_until="networkidle")
    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    assert gen_btn is not None
    assert gen_btn.is_disabled()


def test_whitespace_topic_disabled(page, base_url):
    """纯空格主题时生成按钮 disabled"""
    page.goto(base_url, wait_until="networkidle")
    textarea = page.locator("textarea.code-input-textarea")
    textarea.fill("   ")
    gen_btn = page.locator("button.code-generate-btn")
    assert gen_btn.is_disabled()
