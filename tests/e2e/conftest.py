"""
vibe-blog E2E 测试 — 共享 Playwright Fixtures

功能：
- browser (session): 共享浏览器实例
- context (function): 每测试独立上下文
- page (function): 自动注入 SSE_HOOK_JS
- take_screenshot: 按测试名+步骤名截图
- RUN_E2E_TESTS=1 全局门控
"""
import os
import sys
import time
import pytest

# 将 backend 和 backend/tests 加入 path 以复用 e2e_utils
_backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, _backend_dir)
sys.path.insert(0, os.path.join(_backend_dir, 'tests'))

from e2e_utils import (
    SSE_HOOK_JS,
    FRONTEND_URL,
    BACKEND_URL,
)


# ── 全局门控：RUN_E2E_TESTS=1 才执行 ──

def pytest_collection_modifyitems(config, items):
    if not os.environ.get("RUN_E2E_TESTS"):
        skip = pytest.mark.skip(reason="E2E tests require RUN_E2E_TESTS=1")
        for item in items:
            item.add_marker(skip)


# ── Fixtures ──

@pytest.fixture(scope="session")
def browser():
    """Session-scoped 浏览器实例"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    headed = os.environ.get("E2E_HEADED", "0") == "1"
    slow_mo = int(os.environ.get("E2E_SLOW_MO", "100"))
    b = pw.chromium.launch(headless=not headed, slow_mo=slow_mo)
    yield b
    b.close()
    pw.stop()


@pytest.fixture(scope="session")
def screenshot_dir():
    """截图输出目录"""
    d = os.path.join(
        os.path.dirname(__file__), '..', '..', 'backend', 'outputs', 'e2e_screenshots'
    )
    os.makedirs(d, exist_ok=True)
    return d


@pytest.fixture
def context(browser):
    """Function-scoped 浏览器上下文（每测试隔离 cookies/storage）"""
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    """Function-scoped 页面，自动注入 SSE Hook"""
    p = context.new_page()
    p.set_default_timeout(30_000)
    p.add_init_script(SSE_HOOK_JS)
    yield p
    p.close()


@pytest.fixture
def take_screenshot(page, screenshot_dir, request):
    """返回截图函数: take_screenshot("step_name") -> filepath"""
    test_name = request.node.name

    def _take(step_name: str) -> str:
        ts = time.strftime('%H%M%S')
        path = os.path.join(screenshot_dir, f"{test_name}_{step_name}_{ts}.png")
        page.screenshot(path=path, full_page=True)
        return path

    return _take


@pytest.fixture
def base_url():
    return FRONTEND_URL


@pytest.fixture
def backend_url():
    return BACKEND_URL
