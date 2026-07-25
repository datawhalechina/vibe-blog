"""
TC-13: Dashboard 任务中心（P1）

验证：
- /dashboard 路由可访问
- Queue/Cron 分段视图可切换
- 统计卡片渲染（5 个 stat-card）
- Cron 创建抽屉可打开
- /cron 兼容路由重定向并保留查询参数
- 暗黑模式切换
- API 请求发出（queue/tasks, scheduler/tasks）
"""
import re
import json


def test_dashboard_loads(page, base_url, take_screenshot):
    """Dashboard 页面加载，统计卡片可见"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")
    assert '/dashboard' in page.url

    # 标题
    title = page.locator(".dashboard-title")
    assert title.is_visible()
    assert "$ task-center" in title.text_content()

    # 5 个统计卡片（处理中、等待中、今日完成、失败、已取消）
    stat_cards = page.locator(".stat-card")
    assert stat_cards.count() == 5

    # 标签文字
    labels = page.locator(".stat-label")
    label_texts = [labels.nth(i).text_content() for i in range(labels.count())]
    assert "处理中" in label_texts
    assert "等待中" in label_texts
    assert "今日完成" in label_texts
    assert "失败" in label_texts

    take_screenshot("dashboard_loaded")


def test_dashboard_stats_display_numbers(page, base_url):
    """统计卡片显示数字（即使是 0）"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")

    stat_values = page.locator(".stat-value")
    for i in range(stat_values.count()):
        text = stat_values.nth(i).text_content().strip()
        assert text.isdigit(), f"stat-value[{i}] should be a number, got: {text}"


def test_dashboard_switches_to_cron_view(page, base_url):
    """Cron 标签切换视图并同步 URL。"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")

    assert page.locator('[data-view="queue"]').is_visible()
    page.locator('[data-tab="cron"]').click()
    page.wait_for_url("**/dashboard?tab=cron")
    assert page.locator('[data-view="cron"]').is_visible()
    assert page.locator('[data-tab="cron"]').get_attribute("aria-selected") == "true"


def test_dashboard_opens_cron_drawer(page, base_url, take_screenshot, console_logs):
    """Cron 视图的新建按钮打开任务抽屉。"""
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(f"{base_url}/dashboard?tab=cron", wait_until="networkidle")

    page.locator(".cron-toolbar .primary-button").click()
    drawer = page.locator(".drawer-panel")
    drawer.wait_for(state="visible", timeout=3000)
    assert drawer.locator(".drawer-title").text_content() == "$ new-task"
    assert drawer.locator(".form-input").count() >= 2

    page.wait_for_timeout(400)
    take_screenshot("dashboard_cron_drawer")
    assert page_errors == []
    assert [log for log in console_logs if log["type"] == "error"] == []


def test_dashboard_dark_mode(page, base_url, take_screenshot):
    """暗黑模式切换影响 Dashboard"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")

    container = page.locator(".dashboard-container")

    # 找到主题切换按钮
    toggle = page.locator("button.theme-toggle, .theme-toggle")
    if toggle.count() > 0 and toggle.first.is_visible(timeout=3000):
        # 记录初始状态
        initial_classes = container.get_attribute("class") or ""
        toggle.first.click()
        page.wait_for_timeout(500)
        new_classes = container.get_attribute("class") or ""

        # 状态应该变化
        initial_dark = "dark-mode" in initial_classes
        new_dark = "dark-mode" in new_classes
        assert initial_dark != new_dark, "暗黑模式应该切换"

        take_screenshot("dashboard_dark_mode")

        # 切回
        toggle.first.click()
        page.wait_for_timeout(500)


def test_dashboard_api_requests(page, base_url):
    """Dashboard 加载时应发出 API 请求"""
    api_urls = []

    def on_request(request):
        if '/api/' in request.url:
            api_urls.append(request.url)

    page.on("request", on_request)
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")
    # 等待轮询至少触发一次
    page.wait_for_timeout(1000)

    # 应该请求了 queue/tasks
    queue_requests = [u for u in api_urls if '/api/queue/tasks' in u]
    assert len(queue_requests) >= 1, f"应请求 /api/queue/tasks, 实际: {api_urls}"

    # 应该请求了 scheduler/tasks
    scheduler_requests = [u for u in api_urls if '/api/scheduler/tasks' in u]
    assert len(scheduler_requests) >= 1, f"应请求 /api/scheduler/tasks, 实际: {api_urls}"


def test_dashboard_navigate_from_home(page, base_url):
    """从首页导航到 Dashboard（如果导航栏有链接）"""
    page.goto(base_url, wait_until="networkidle")

    # 尝试找到任务中心链接
    link = page.locator("a:has-text('任务中心'), a[href='/dashboard']")
    if link.count() > 0 and link.first.is_visible(timeout=3000):
        link.first.click()
        page.wait_for_url("**/dashboard", timeout=10000)
        assert '/dashboard' in page.url
    else:
        # 导航栏可能还没加入 Dashboard 链接，直接访问
        page.goto(f"{base_url}/dashboard", wait_until="networkidle")
        assert '/dashboard' in page.url


def test_dashboard_mobile_cron_drawer_fits_viewport(browser, base_url):
    """移动端可切换 Cron，且创建抽屉保持在视口内。"""
    context = browser.new_context(viewport={"width": 375, "height": 812}, locale="zh-CN")
    page = context.new_page()
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{base_url}/dashboard", wait_until="networkidle")
    assert page.locator('[data-tab="queue"]').is_visible()
    assert page.locator('[data-tab="cron"]').is_visible()
    page.locator('[data-tab="cron"]').click()
    page.locator(".cron-toolbar .primary-button").click()
    drawer = page.locator(".drawer-panel")
    drawer.wait_for(state="visible", timeout=3000)
    page.wait_for_timeout(400)

    box = drawer.bounding_box()
    assert box is not None
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= 375
    assert page_errors == []

    page.close()
    context.close()


def test_cron_manager_keeps_supported_actions_without_history(page, base_url, console_logs):
    """旧 Cron URL 重定向后保留查询参数和所有后端支持的任务操作。"""
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    job = {
        "id": "cron-e2e-1",
        "name": "E2E cron",
        "enabled": True,
        "schedule": {"kind": "cron", "expr": "0 9 * * *"},
        "last_status": "error",
        "last_error": "timeout",
        "consecutive_errors": 1,
        "generation": {"topic": "E2E"},
        "tags": [],
    }

    page.route(
        "**/api/scheduler/tasks",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps([job]),
        ),
    )
    page.goto(f"{base_url}/cron?source=e2e", wait_until="networkidle")

    assert re.search(r"/dashboard\?(?:source=e2e&tab=cron|tab=cron&source=e2e)$", page.url)
    assert page.locator('[data-view="cron"]').is_visible()

    assert page.locator('button[title="编辑"]').count() == 0
    for title in ("暂停", "执行", "重试", "删除"):
        assert page.locator(f'button[title="{title}"]').is_visible()
    assert page.locator('button[title="历史"]').count() == 0
    assert page_errors == []
    assert [log for log in console_logs if log["type"] == "error"] == []
