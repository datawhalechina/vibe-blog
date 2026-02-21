"""
TC-13: Dashboard 任务中心（P1）

验证：
- /dashboard 路由可访问
- 统计卡片渲染（4 个 stat-card）
- 定时任务区块存在
- 暗黑模式切换
- API 请求发出（queue/tasks, scheduler/tasks）
"""
import re


def test_dashboard_loads(page, base_url, take_screenshot):
    """Dashboard 页面加载，统计卡片可见"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")
    assert '/dashboard' in page.url

    # 标题
    title = page.locator(".dashboard-title")
    assert title.is_visible()
    assert "任务中心" in title.text_content()

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


def test_dashboard_scheduled_section(page, base_url):
    """定时任务区块存在，有新建按钮"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")

    # 定时任务标题
    section_headers = page.locator(".task-section h2, .section-header h2")
    found = False
    for i in range(section_headers.count()):
        if "定时任务" in section_headers.nth(i).text_content():
            found = True
            break
    assert found, "应该有'定时任务'区块"

    # 新建按钮
    add_btn = page.locator(".btn-add")
    assert add_btn.is_visible()
    assert "+ 新建" in add_btn.text_content()


def test_dashboard_schedule_form_toggle(page, base_url, take_screenshot):
    """点击新建按钮展开/收起定时任务表单"""
    page.goto(f"{base_url}/dashboard", wait_until="networkidle")

    add_btn = page.locator(".btn-add")
    # 表单初始不可见
    assert page.locator(".schedule-form").count() == 0

    # 点击展开
    add_btn.click()
    form = page.locator(".schedule-form")
    form.wait_for(state="visible", timeout=3000)
    assert form.is_visible()

    # 表单内有输入框
    inputs = form.locator(".form-input")
    assert inputs.count() >= 2

    take_screenshot("schedule_form_open")

    # 点击收起
    add_btn.click()
    page.wait_for_timeout(500)
    assert page.locator(".schedule-form").count() == 0


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
