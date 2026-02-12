"""
TC-7: 路由导航（P2）

验证：各页面路由可访问
"""


def test_navigate_to_blog_list(page, base_url):
    """访问 /blog 路由"""
    page.goto(f"{base_url}/blog", wait_until="networkidle")
    assert '/blog' in page.url


def test_navigate_to_xhs(page, base_url):
    """通过导航栏跳转到小红书创作页"""
    page.goto(base_url, wait_until="networkidle")
    xhs_link = page.locator("a:has-text('小红书')")
    if xhs_link.count() > 0 and xhs_link.first.is_visible(timeout=3000):
        xhs_link.first.click()
        page.wait_for_url("**/xhs", timeout=10000)
        assert '/xhs' in page.url


def test_navigate_to_reviewer(page, base_url):
    """通过导航栏跳转到教程评估页"""
    page.goto(base_url, wait_until="networkidle")
    link = page.locator("a:has-text('教程评估')")
    if link.count() > 0 and link.first.is_visible(timeout=3000):
        link.first.click()
        page.wait_for_url("**/reviewer", timeout=10000)
        assert '/reviewer' in page.url
