"""
TC-10: 博客详情页（P2）

验证：从历史 API 获取 blog_id → 访问详情页 → 内容区域可见
"""
import pytest
import requests


def test_blog_detail_page(page, base_url, backend_url, take_screenshot):
    """博客详情页正确渲染"""
    # 从 history API 获取一个 blog_id
    try:
        resp = requests.get(f"{backend_url}/api/history?page=1&page_size=1", timeout=10)
        data = resp.json()
        records = data.get("records", [])
        if not records:
            pytest.skip("无历史记录，跳过详情页测试")
        blog_id = records[0].get("id") or records[0].get("task_id")
    except Exception:
        pytest.skip("后端不可达或无历史记录")

    page.goto(f"{base_url}/blog/{blog_id}", wait_until="networkidle")
    page.wait_for_timeout(3000)
    take_screenshot("blog_detail")

    # 内容区域应可见
    content = page.locator(".content-area")
    assert content.is_visible(timeout=10000), "博客内容区域不可见"
