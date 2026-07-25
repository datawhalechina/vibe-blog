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


def test_retired_reviewer_redirects_home(page, base_url, console_logs):
    """教程评估入口已移除，旧地址兼容跳转首页"""
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(base_url, wait_until="networkidle")
    link = page.locator("a:has-text('教程评估')")
    assert link.count() == 0

    page.goto(f"{base_url}/reviewer", wait_until="networkidle")
    page.wait_for_url(f"{base_url}/", timeout=10000)
    assert page.url == f"{base_url}/"
    assert [log for log in console_logs if log["type"] == "error"] == []
    assert page_errors == []
