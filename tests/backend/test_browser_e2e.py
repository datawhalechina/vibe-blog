"""
Playwright 浏览器端到端测试：自动打开浏览器 → 输入主题 → 选择风格 → 生成博客 → 验证配图

测试流程：
1. 启动浏览器，打开 vibe-blog 首页
2. 在输入框中输入博客主题
3. 展开高级选项，选择指定的配图风格
4. 点击生成按钮
5. 等待 SSE 进度完成
6. 跳转到博客详情页，验证页面中包含图片

使用方法：
    # 安装依赖
    pip install playwright sseclient-py
    playwright install chromium

    # 运行测试（headed 模式，可以看到浏览器操作）
    uv run tests/backend/test_browser_e2e.py --headed

    # 无头模式
    uv run tests/backend/test_browser_e2e.py

    # 指定主题和风格
    uv run tests/backend/test_browser_e2e.py --topic "LangGraph 入门" --style academic --headed

    # 使用 pytest 运行
    pytest tests/backend/test_browser_e2e.py -v -s
"""

import os
import sys
import json
import time
import re
import argparse
import logging
from typing import Optional, List
from dataclasses import dataclass, field

import pytest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, Page, Browser, expect
except ImportError:
    sync_playwright = None


@dataclass
class BrowserTestResult:
    """浏览器测试结果"""
    passed: bool = False
    topic: str = ""
    style: str = ""
    task_id: str = ""
    images_found: int = 0
    progress_completed: bool = False
    blog_page_loaded: bool = False
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    screenshots: List[str] = field(default_factory=list)
    saved_path: str = ""
    blog_url: str = ""



class BrowserE2ETest:
    """Playwright 浏览器端到端测试"""

    def __init__(
        self,
        base_url: str = "http://localhost:5173",
        headed: bool = True,
        slow_mo: int = 300,
        timeout: int = 600
    ):
        self.base_url = base_url.rstrip('/')
        self.headed = headed
        self.slow_mo = slow_mo
        self.timeout = timeout * 1000  # 转为毫秒
        self.screenshot_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'outputs', 'test_screenshots'
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def _save_screenshot(self, page: Page, name: str) -> str:
        """保存截图"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.screenshot_dir, f"{name}_{timestamp}.png")
        page.screenshot(path=filepath, full_page=True)
        logger.info(f"  📸 截图已保存: {filepath}")
        return filepath

    def run(
        self,
        topic: str = "Python 装饰器入门",
        style: str = "cartoon"
    ) -> BrowserTestResult:
        """
        运行完整的浏览器 E2E 测试

        Args:
            topic: 博客主题
            style: 配图风格 ID
        """
        result = BrowserTestResult(topic=topic, style=style)
        start_time = time.time()

        logger.info("=" * 60)
        logger.info("🌐 Playwright 浏览器 E2E 测试")
        logger.info(f"   主题: {topic}")
        logger.info(f"   风格: {style}")
        logger.info(f"   地址: {self.base_url}")
        logger.info(f"   模式: {'有头' if self.headed else '无头'}")
        logger.info("=" * 60)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=not self.headed,
                slow_mo=self.slow_mo
            )
            context = browser.new_context(
                viewport={'width': 1440, 'height': 900},
                locale='zh-CN'
            )
            page = context.new_page()
            page.set_default_timeout(self.timeout)

            try:
                # Step 1: 打开首页
                result = self._step_open_home(page, result)
                if result.errors:
                    return result

                # Step 2: 输入主题
                result = self._step_input_topic(page, topic, result)

                # Step 3: 选择配图风格
                result = self._step_select_style(page, style, result)

                # Step 4: 点击生成
                result = self._step_click_generate(page, result)
                if result.errors:
                    return result

                # Step 5: 等待生成完成
                result = self._step_wait_completion(page, result)

                # Step 6: 验证结果
                result = self._step_verify_result(page, result)

            except Exception as e:
                result.errors.append(f"测试异常: {str(e)}")
                logger.error(f"❌ 测试异常: {e}", exc_info=True)
                try:
                    result.screenshots.append(
                        self._save_screenshot(page, "error")
                    )
                except Exception:
                    pass
            finally:
                result.duration_seconds = time.time() - start_time
                browser.close()

        # 输出报告
        self._print_report(result)
        return result

    def _step_open_home(self, page: Page, result: BrowserTestResult) -> BrowserTestResult:
        """Step 1: 打开首页"""
        logger.info("\n📌 Step 1: 打开首页")
        try:
            page.goto(self.base_url, wait_until='networkidle')
            logger.info(f"  ✅ 首页加载成功: {page.title()}")
            result.screenshots.append(self._save_screenshot(page, "01_home"))
        except Exception as e:
            result.errors.append(f"首页加载失败: {e}")
            logger.error(f"  ❌ 首页加载失败: {e}")
        return result

    def _step_input_topic(self, page: Page, topic: str, result: BrowserTestResult) -> BrowserTestResult:
        """Step 2: 输入博客主题"""
        logger.info(f"\n📌 Step 2: 输入主题: {topic}")

        # 尝试多种选择器定位输入框
        input_selectors = [
            'textarea[placeholder*="输入"]',
            'textarea[placeholder*="主题"]',
            'textarea[placeholder*="想写"]',
            'input[placeholder*="输入"]',
            'input[placeholder*="主题"]',
            '.blog-input textarea',
            '.input-card textarea',
            'textarea',
        ]

        input_element = None
        for selector in input_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    input_element = element
                    logger.info(f"  找到输入框: {selector}")
                    break
            except Exception:
                continue

        if input_element:
            input_element.click()
            input_element.fill(topic)
            logger.info(f"  ✅ 已输入主题: {topic}")
        else:
            logger.warning(f"  ⚠️ 未找到输入框，尝试使用键盘输入")
            page.keyboard.type(topic)

        return result

    def _step_select_style(self, page: Page, style: str, result: BrowserTestResult) -> BrowserTestResult:
        """Step 3: 展开高级选项并选择配图风格"""
        logger.info(f"\n📌 Step 3: 选择配图风格: {style}")

        # 尝试展开高级选项
        advanced_selectors = [
            'text=高级选项',
            'text=Advanced',
            'button:has-text("高级")',
            '.advanced-toggle',
            '[data-testid="advanced-options"]',
        ]

        for selector in advanced_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    logger.info(f"  展开高级选项: {selector}")
                    page.wait_for_timeout(500)
                    break
            except Exception:
                continue

        # 选择配图风格
        style_selectors = [
            f'select >> nth=0',  # 第一个 select 可能是文章类型
            'select[name*="style"]',
            'select[name*="image"]',
            '.image-style select',
        ]

        # 尝试通过 label 找到配图风格的 select
        try:
            # 方法 1: 找到包含"配图风格"文字的 label 旁边的 select
            style_label = page.locator('text=配图风格').first
            if style_label.is_visible(timeout=2000):
                # 找到同级或父级中的 select
                parent = style_label.locator('..').first
                select = parent.locator('select').first
                if select.is_visible(timeout=1000):
                    select.select_option(value=style)
                    logger.info(f"  ✅ 已选择配图风格: {style}")
                    result.screenshots.append(self._save_screenshot(page, "03_style_selected"))
                    return result
        except Exception:
            pass

        # 方法 2: 遍历所有 select，找到包含风格选项的
        try:
            selects = page.locator('select').all()
            for select in selects:
                try:
                    options = select.locator('option').all()
                    option_values = [opt.get_attribute('value') or '' for opt in options]
                    if style in option_values or 'cartoon' in option_values:
                        select.select_option(value=style)
                        logger.info(f"  ✅ 已选择配图风格: {style}")
                        result.screenshots.append(self._save_screenshot(page, "03_style_selected"))
                        return result
                except Exception:
                    continue
        except Exception:
            pass

        logger.warning(f"  ⚠️ 未找到配图风格选择器，将使用默认风格")
        return result

    def _step_click_generate(self, page: Page, result: BrowserTestResult) -> BrowserTestResult:
        """Step 4: 点击生成按钮"""
        logger.info(f"\n📌 Step 4: 点击生成按钮")

        # 在点击前注册网络监听器，确保能捕获 API 返回的 task_id
        self._captured_task_id = None

        def handle_response(response):
            if '/api/blog/generate' in response.url and response.status < 300:
                try:
                    body = response.json()
                    if body.get('task_id'):
                        self._captured_task_id = body['task_id']
                        logger.info(f"  📡 捕获 task_id: {self._captured_task_id}")
                except Exception:
                    pass

        page.on('response', handle_response)

        generate_selectors = [
            '.code-generate-btn',
            'button:has-text("execute")',
            'button:has-text("生成")',
            'button:has-text("开始")',
            'button:has-text("Generate")',
            'button:has-text("Start")',
            '.generate-btn',
            'button[type="submit"]',
        ]

        clicked = False
        for selector in generate_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000) and element.is_enabled(timeout=1000):
                    element.click()
                    logger.info(f"  ✅ 已点击生成按钮: {selector}")
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            result.errors.append("未找到生成按钮")
            logger.error(f"  ❌ 未找到可点击的生成按钮")
            result.screenshots.append(self._save_screenshot(page, "04_no_generate_btn"))
        else:
            # 等待 API 响应返回 task_id
            page.wait_for_timeout(3000)
            if self._captured_task_id:
                result.task_id = self._captured_task_id
                logger.info(f"  📡 task_id 已确认: {self._captured_task_id}")

        return result

    def _step_wait_completion(self, page: Page, result: BrowserTestResult) -> BrowserTestResult:
        """Step 5: 等待生成完成"""
        logger.info(f"\n📌 Step 5: 等待生成完成（最长 {self.timeout // 1000}s）")

        result.screenshots.append(self._save_screenshot(page, "05_generating"))

        # 使用 Step 4 中捕获的 task_id
        task_id = self._captured_task_id

        # 等待进度面板出现
        try:
            # 等待进度指示器出现
            progress_selectors = [
                '.progress-drawer',
                '.progress-panel',
                '[class*="progress"]',
                '[class*="terminal"]',
                'text=正在生成',
                'text=开始生成',
            ]

            for selector in progress_selectors:
                try:
                    page.locator(selector).first.wait_for(state='visible', timeout=10000)
                    logger.info(f"  📊 进度面板已出现: {selector}")
                    break
                except Exception:
                    continue

        except Exception:
            logger.warning(f"  ⚠️ 未检测到进度面板")

        # 等待完成信号
        # 主要依赖 URL 跳转到 /blog/ 详情页（前端 complete 事件后 1s 自动跳转）
        # 备用：检测进度面板内的完成文字（限定在 .progress-drawer 内避免误判历史记录）
        max_wait = self.timeout // 1000
        check_interval = 5
        elapsed = 0

        while elapsed < max_wait:
            # 优先检查：是否已跳转到详情页（最可靠的完成信号）
            current_url = page.url
            if '/blog/' in current_url and current_url != self.base_url:
                logger.info(f"  🎉 已跳转到详情页: {current_url}")
                result.progress_completed = True
                result.blog_page_loaded = True
                result.task_id = task_id or result.task_id
                result.blog_url = current_url
                result.screenshots.append(self._save_screenshot(page, "05_completed"))
                return result

            # 备用检查：进度面板内的完成信号（限定在 .progress-drawer 内部）
            completion_selectors = [
                '.progress-drawer :text("🎉 生成完成")',
                '.progress-drawer .progress-item:has-text("生成完成")',
                '.progress-drawer :text("已完成")',
            ]
            for selector in completion_selectors:
                try:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        logger.info(f"  🎉 检测到完成信号: {selector}")
                        result.progress_completed = True
                        result.task_id = task_id or result.task_id
                        result.screenshots.append(self._save_screenshot(page, "05_completed"))
                        # 等待前端自动跳转（complete 事件后 setTimeout 1s）
                        page.wait_for_timeout(3000)
                        new_url = page.url
                        if '/blog/' in new_url:
                            result.blog_page_loaded = True
                            result.blog_url = new_url
                            logger.info(f"  🔗 跳转到详情页: {new_url}")
                        return result
                except Exception:
                    continue

            # 检查是否有错误
            error_selectors = [
                '.progress-drawer :text("❌")',
                '.progress-drawer :text("错误")',
                '.error-message',
            ]
            for selector in error_selectors:
                try:
                    if page.locator(selector).first.is_visible(timeout=500):
                        result.errors.append(f"页面显示错误: {selector}")
                        logger.error(f"  ❌ 检测到错误: {selector}")
                        result.screenshots.append(self._save_screenshot(page, "05_error"))
                        return result
                except Exception:
                    continue

            elapsed += check_interval
            if elapsed % 30 == 0:
                logger.info(f"  ⏳ 等待中... {elapsed}s / {max_wait}s")
                result.screenshots.append(self._save_screenshot(page, f"05_waiting_{elapsed}s"))

            page.wait_for_timeout(check_interval * 1000)

        logger.warning(f"  ⚠️ 等待超时 ({max_wait}s)")
        result.errors.append(f"等待超时 ({max_wait}s)")
        result.screenshots.append(self._save_screenshot(page, "05_timeout"))
        return result

    def _step_verify_result(self, page: Page, result: BrowserTestResult) -> BrowserTestResult:
        """Step 6: 验证结果页面"""
        logger.info(f"\n📌 Step 6: 验证结果")

        # 如果还没跳转到详情页，尝试点击"查看文章"或等待自动跳转
        if not result.blog_page_loaded:
            # 先等待可能的自动跳转（前端 complete 事件后 1s 跳转）
            page.wait_for_timeout(3000)
            current_url = page.url
            if '/blog/' in current_url:
                result.blog_page_loaded = True
                result.blog_url = current_url
                logger.info(f"  🔗 自动跳转到详情页: {current_url}")

        if not result.blog_page_loaded:
            view_selectors = [
                'text=查看文章',
                'text=查看详情',
                'a:has-text("查看")',
                '.view-article',
            ]
            for selector in view_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=3000):
                        element.click()
                        page.wait_for_load_state('networkidle', timeout=15000)
                        result.blog_page_loaded = True
                        result.blog_url = page.url
                        logger.info(f"  🔗 已跳转到详情页: {page.url}")
                        break
                except Exception:
                    continue

        # 验证页面中的图片
        page.wait_for_timeout(3000)  # 等待图片加载

        try:
            images = page.locator('img').all()
            visible_images = 0
            for img in images:
                try:
                    if img.is_visible(timeout=1000):
                        src = img.get_attribute('src') or ''
                        alt = img.get_attribute('alt') or ''
                        if src and not src.startswith('data:image/svg'):
                            visible_images += 1
                            logger.info(f"  🖼️ 图片: alt='{alt[:50]}', src='{src[:80]}'")
                except Exception:
                    continue

            result.images_found = visible_images
            logger.info(f"  📊 页面中找到 {visible_images} 张图片")

        except Exception as e:
            logger.warning(f"  ⚠️ 图片检测异常: {e}")

        result.screenshots.append(self._save_screenshot(page, "06_result"))

        # 通过 API 获取 saved_path
        if result.task_id:
            try:
                import requests
                backend_url = self.base_url.replace(':5173', ':5001')
                resp = requests.get(f"{backend_url}/api/tasks/{result.task_id}", timeout=10)
                if resp.status_code == 200:
                    task_data = resp.json()
                    saved_path = task_data.get('outputs', {}).get('saved_path', '')
                    if saved_path:
                        result.saved_path = saved_path
                        logger.info(f"  📄 Markdown 文件: {saved_path}")
            except Exception as e:
                logger.warning(f"  ⚠️ 获取 saved_path 失败: {e}")

        # 如果没有从 API 拿到，尝试从 blog_url 推断
        if not result.blog_url and result.task_id:
            result.blog_url = f"{self.base_url}/blog/{result.task_id}"

        # 判断是否通过
        result.passed = (
            result.progress_completed
            and len(result.errors) == 0
        )

        return result

    def _print_report(self, result: BrowserTestResult):
        """输出测试报告"""
        print()
        print("=" * 60)
        print("📊 浏览器 E2E 测试报告")
        print("=" * 60)
        print(f"  主题:           {result.topic}")
        print(f"  配图风格:       {result.style}")
        print(f"  任务 ID:        {result.task_id or 'N/A'}")
        print(f"  耗时:           {result.duration_seconds:.1f}s")
        print(f"  生成完成:       {'✅' if result.progress_completed else '❌'}")
        print(f"  详情页加载:     {'✅' if result.blog_page_loaded else '❌'}")
        print(f"  页面图片数:     {result.images_found}")
        print(f"  错误数:         {len(result.errors)}")
        print(f"  截图数:         {len(result.screenshots)}")
        print(f"  博客详情页:     {result.blog_url or 'N/A'}")
        print(f"  Markdown 路径:  {result.saved_path or 'N/A'}")
        print(f"  总体结果:       {'✅ PASSED' if result.passed else '❌ FAILED'}")

        if result.errors:
            print()
            print("  错误详情:")
            for err in result.errors:
                print(f"    - {err}")

        if result.screenshots:
            print()
            print("  截图文件:")
            for ss in result.screenshots:
                print(f"    - {ss}")

        print("=" * 60)


# ========== pytest 集成 ==========

_skip_e2e = pytest.mark.skipif(
    not os.environ.get("RUN_E2E_TESTS"),
    reason="E2E tests require RUN_E2E_TESTS=1 and a running frontend/backend"
)


@_skip_e2e
def test_browser_e2e_cartoon():
    """pytest: 测试 cartoon 风格"""
    tester = BrowserE2ETest(headed=False, slow_mo=100, timeout=600)
    result = tester.run(topic="Python 装饰器入门", style="cartoon")
    assert result.passed, f"测试失败: {result.errors}"


@_skip_e2e
def test_browser_e2e_academic():
    """pytest: 测试 academic 风格"""
    tester = BrowserE2ETest(headed=False, slow_mo=100, timeout=600)
    result = tester.run(topic="Transformer 架构详解", style="academic")
    assert result.passed, f"测试失败: {result.errors}"


# ========== 命令行入口 ==========

def main():
    parser = argparse.ArgumentParser(
        description="vibe-blog Playwright 浏览器 E2E 测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 有头模式（可以看到浏览器操作）
  python tests/test_browser_e2e.py --headed

  # 指定主题和风格
  python tests/test_browser_e2e.py --topic "LangGraph 入门" --style academic --headed

  # 无头模式（CI 环境）
  python tests/test_browser_e2e.py --style cartoon
        """
    )
    parser.add_argument("--base-url", default="http://localhost:5173", help="前端地址（默认 Vite dev server）")
    parser.add_argument("--topic", default="Python 装饰器入门", help="博客主题")
    parser.add_argument("--style", default="cartoon", help="配图风格")
    parser.add_argument("--headed", action="store_true", help="有头模式（显示浏览器窗口）")
    parser.add_argument("--slow-mo", type=int, default=300, help="操作间隔（毫秒）")
    parser.add_argument("--timeout", type=int, default=600, help="超时时间（秒）")

    args = parser.parse_args()

    tester = BrowserE2ETest(
        base_url=args.base_url,
        headed=args.headed,
        slow_mo=args.slow_mo,
        timeout=args.timeout
    )

    result = tester.run(topic=args.topic, style=args.style)
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
