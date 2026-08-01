"""
TC-17: Storybook completion contract (P1)

Verify the real ``{task_id, status, outputs}`` completion envelope renders a
preview on Home without assuming that a persisted book route exists.
"""
import json
from urllib.parse import urlparse

from playwright.sync_api import expect

from e2e_utils import (
    GENERATE_BTN_SELECTORS,
    INPUT_SELECTORS,
    fill_input,
    find_element,
)


def test_storybook_completion_renders_preview_on_home(
    page,
    base_url,
    console_logs,
    take_screenshot,
):
    task_id = "storybook-contract-e2e"
    outputs = {
        "title": "缓存小镇历险记",
        "subtitle": "一次穿越高速数据通道的旅程",
        "core_metaphor": "缓存就像离家更近的便利店",
        "pages": [
            {
                "page_number": 1,
                "title": "第一页：出发",
                "content": "小码发现，常用数据放得越近，读取速度就越快。",
                "key_takeaway": "缓存用空间换取时间。",
            },
        ],
    }

    page.route(
        "**/api/config",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": True, "features": {}}),
        ),
    )
    page.route(
        "**/api/image-styles",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": True, "styles": []}),
        ),
    )
    page.route(
        "**/api/history**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": True, "records": [], "total": 0}),
        ),
    )

    page.route(
        "**/api/generate",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": True, "task_id": task_id}),
        ),
    )

    sse_body = "".join(
        [
            "event: connected\n",
            f"data: {json.dumps({'task_id': task_id, 'status': 'connected'}, ensure_ascii=False)}\n\n",
            "event: complete\n",
            f"data: {json.dumps({'task_id': task_id, 'status': 'completed', 'outputs': outputs}, ensure_ascii=False)}\n\n",
        ]
    )
    page.route(
        f"**/api/tasks/{task_id}/stream",
        lambda route: route.fulfill(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
            },
            body=sse_body,
        ),
    )

    page.goto(base_url, wait_until="networkidle")

    input_el, _ = find_element(page, INPUT_SELECTORS)
    assert input_el is not None, f"未找到主题输入框，尝试过: {INPUT_SELECTORS}"
    fill_input(page, input_el, "用绘本解释缓存")

    page.get_by_role("button", name="高级选项").click()
    page.locator(".advanced-options-panel select").first.select_option("storybook")

    gen_btn, _ = find_element(page, GENERATE_BTN_SELECTORS)
    assert gen_btn is not None, f"未找到生成按钮，尝试过: {GENERATE_BTN_SELECTORS}"
    gen_btn.click()

    preview_tab = page.get_by_role("button", name="$ cat preview.md")
    preview_tab.wait_for(state="visible")
    expect(preview_tab).to_be_enabled()
    preview_tab.click()

    preview = page.locator(".progress-preview-content")
    preview.locator("h1", has_text=outputs["title"]).wait_for(state="visible")
    assert preview.locator("h2", has_text=outputs["pages"][0]["title"]).is_visible()
    assert preview.get_by_text(outputs["pages"][0]["content"], exact=True).is_visible()
    assert urlparse(page.url).path == "/"

    # The removed implementation scheduled navigation after one second.
    page.wait_for_timeout(1_250)
    assert urlparse(page.url).path == "/"
    assert not [log for log in console_logs if log["type"] == "error"]
    take_screenshot("storybook_preview")
