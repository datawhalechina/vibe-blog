"""
Playwright 验证脚本：生成 mini 文章并检查 Markdown 排版问题

验证目标：
1. ---## 连写问题是否修复
2. 文本紧挨 --- 导致 Setext 标题（加粗）问题是否修复

使用方法：
    python tests/test_markdown_fix.py --headed
"""

import os
import sys
import json
import time
import re
import argparse
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("请先安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


def verify_markdown_formatting(task_id: str, backend_url: str) -> dict:
    """通过 API 获取文章内容并验证 Markdown 格式"""
    result = {
        "task_id": task_id,
        "has_dash_hash_concat": False,  # ---## 连写
        "has_setext_heading": False,     # 文本紧挨 ---
        "dash_hash_count": 0,
        "setext_count": 0,
        "details": [],
        "passed": True
    }

    try:
        resp = requests.get(f"{backend_url}/api/history/{task_id}", timeout=10)
        if resp.status_code != 200:
            result["details"].append(f"API 返回 {resp.status_code}")
            result["passed"] = False
            return result

        data = resp.json()
        if not data.get("success"):
            result["details"].append("API 返回 success=false")
            result["passed"] = False
            return result

        md = data["record"].get("markdown_content", "")
        if not md:
            result["details"].append("markdown_content 为空")
            result["passed"] = False
            return result

        # 检查 1: ---## 连写
        matches1 = re.findall(r'.{0,40}---##.{0,40}', md)
        if matches1:
            result["has_dash_hash_concat"] = True
            result["dash_hash_count"] = len(matches1)
            result["passed"] = False
            for m in matches1[:3]:
                result["details"].append(f"---## 连写: {repr(m)}")

        # 检查 2: 文本紧挨 ---（非空行后直接跟 ---）
        # Setext 标题：非空行 + \n + --- 会被解析为 H2
        matches2 = re.findall(r'[^\n]\n---\n', md)
        if matches2:
            result["has_setext_heading"] = True
            result["setext_count"] = len(matches2)
            result["passed"] = False
            for m in matches2[:3]:
                result["details"].append(f"文本紧挨---: {repr(m)}")

        # 检查 3: 确保所有 --- 前后都有空行
        lines = md.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == '---':
                # 检查前一行是否为空
                if i > 0 and lines[i-1].strip() != '':
                    result["passed"] = False
                    context = lines[i-1][:50]
                    result["details"].append(f"第{i+1}行 --- 前无空行，前一行: {repr(context)}")
                # 检查后一行是否为空
                if i < len(lines) - 1 and lines[i+1].strip() != '':
                    result["passed"] = False
                    context = lines[i+1][:50]
                    result["details"].append(f"第{i+1}行 --- 后无空行，后一行: {repr(context)}")

        if result["passed"]:
            result["details"].append("所有 --- 分隔线格式正确")

    except Exception as e:
        result["details"].append(f"验证异常: {e}")
        result["passed"] = False

    return result


def run_test(headed: bool = True, timeout: int = 600):
    """运行 Playwright 测试"""
    base_url = "http://localhost:5173"
    backend_url = "http://localhost:5001"

    logger.info("=" * 60)
    logger.info("🔍 Markdown 排版修复验证测试")
    logger.info(f"   模式: mini（快速生成）")
    logger.info(f"   前端: {base_url}")
    logger.info(f"   后端: {backend_url}")
    logger.info("=" * 60)

    # 先验证已有文章（前端修复）
    logger.info("\n📋 Phase 1: 验证已有文章（前端 fixMarkdownSeparators）")
    existing_result = verify_markdown_formatting("task_e7b4c252ca22", backend_url)
    if existing_result["has_dash_hash_concat"] or existing_result["has_setext_heading"]:
        logger.info("  ⚠️ 已有文章数据中存在格式问题（预期，前端渲染时会修复）")
        for d in existing_result["details"]:
            logger.info(f"    - {d}")
    else:
        logger.info("  ✅ 已有文章数据格式正常")

    # Phase 2: 生成新文章
    logger.info("\n📋 Phase 2: 生成新 mini 文章验证后端修复")

    captured_task_id = None
    start_time = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            slow_mo=200
        )
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            locale='zh-CN'
        )
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)

        try:
            # Step 1: 打开首页
            logger.info("\n📌 Step 1: 打开首页")
            page.goto(base_url, wait_until='networkidle')
            logger.info(f"  ✅ 首页加载成功")

            # Step 2: 输入主题
            logger.info("\n📌 Step 2: 输入主题")
            topic = "Python 列表推导式入门"
            textarea = page.locator('textarea').first
            textarea.click()
            textarea.fill(topic)
            logger.info(f"  ✅ 已输入: {topic}")

            # Step 3: 展开高级选项 → 选择 mini 长度
            logger.info("\n📌 Step 3: 选择 mini 文章长度")
            # 点击高级选项
            advanced_btn = page.locator('text=高级选项').first
            if advanced_btn.is_visible(timeout=3000):
                advanced_btn.click()
                page.wait_for_timeout(500)
                logger.info("  展开高级选项")

            # 选择文章长度为 mini
            selects = page.locator('.advanced-options-panel select').all()
            if len(selects) >= 2:
                selects[1].select_option(value='mini')
                logger.info("  ✅ 已选择文章长度: mini")
            else:
                logger.warning(f"  ⚠️ 找到 {len(selects)} 个 select，尝试其他方式")
                # 备用：遍历所有 select 找包含 mini 选项的
                for s in page.locator('select').all():
                    options = [opt.get_attribute('value') for opt in s.locator('option').all()]
                    if 'mini' in options:
                        s.select_option(value='mini')
                        logger.info("  ✅ 已选择文章长度: mini（备用方式）")
                        break

            # Step 4: 注册网络监听 + 点击生成
            logger.info("\n📌 Step 4: 点击生成")

            def handle_response(response):
                nonlocal captured_task_id
                if '/api/blog/generate' in response.url and response.status < 300:
                    try:
                        body = response.json()
                        if body.get('task_id'):
                            captured_task_id = body['task_id']
                            logger.info(f"  📡 捕获 task_id: {captured_task_id}")
                    except Exception:
                        pass

            page.on('response', handle_response)

            gen_btn = page.locator('.code-generate-btn').first
            if gen_btn.is_visible(timeout=3000):
                gen_btn.click()
                logger.info("  ✅ 已点击生成按钮")
            else:
                logger.error("  ❌ 未找到生成按钮")
                browser.close()
                return False

            page.wait_for_timeout(3000)
            if captured_task_id:
                logger.info(f"  📡 task_id 确认: {captured_task_id}")

            # Step 5: 等待完成
            logger.info(f"\n📌 Step 5: 等待生成完成（最长 {timeout}s）")
            max_wait = timeout
            elapsed = 0
            check_interval = 5

            while elapsed < max_wait:
                # 检查 URL 跳转
                if '/blog/' in page.url:
                    logger.info(f"  🎉 已跳转到详情页: {page.url}")
                    break

                # 检查进度面板完成信号
                try:
                    drawer = page.locator('.progress-drawer')
                    if drawer.is_visible(timeout=500):
                        if drawer.locator(':text("生成完成")').is_visible(timeout=500):
                            logger.info("  🎉 检测到生成完成信号")
                            page.wait_for_timeout(3000)
                            break
                except Exception:
                    pass

                elapsed += check_interval
                if elapsed % 30 == 0:
                    logger.info(f"  ⏳ 等待中... {elapsed}s / {max_wait}s")
                page.wait_for_timeout(check_interval * 1000)

            if elapsed >= max_wait:
                logger.error(f"  ❌ 等待超时 ({max_wait}s)")
                browser.close()
                return False

            # Step 6: 验证 Markdown 格式
            logger.info(f"\n📌 Step 6: 验证新文章 Markdown 格式")
            page.wait_for_timeout(2000)

            task_id = captured_task_id
            if not task_id and '/blog/' in page.url:
                task_id = page.url.split('/blog/')[-1].split('?')[0]

            if task_id:
                verify_result = verify_markdown_formatting(task_id, backend_url)
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 Markdown 排版验证报告")
                logger.info(f"{'='*60}")
                logger.info(f"  task_id:        {task_id}")
                logger.info(f"  ---## 连写:     {'❌ 存在' if verify_result['has_dash_hash_concat'] else '✅ 无'}")
                logger.info(f"  文本紧挨---:    {'❌ 存在' if verify_result['has_setext_heading'] else '✅ 无'}")
                logger.info(f"  详情:")
                for d in verify_result["details"]:
                    logger.info(f"    - {d}")
                logger.info(f"  总体结果:       {'✅ PASSED' if verify_result['passed'] else '❌ FAILED'}")
                logger.info(f"  博客详情页:     {base_url}/blog/{task_id}")
                logger.info(f"  耗时:           {time.time() - start_time:.1f}s")
                logger.info(f"{'='*60}")

                # 同时验证前端渲染
                logger.info("\n📌 Step 7: 验证前端渲染（检查页面中是否有异常加粗）")
                if '/blog/' in page.url:
                    page.wait_for_timeout(2000)
                    # 检查是否有 ---## 在页面中显示为异常文本
                    page_text = page.inner_text('body')
                    if '---##' in page_text:
                        logger.error("  ❌ 页面中仍然显示 ---## 文本")
                        verify_result["passed"] = False
                    else:
                        logger.info("  ✅ 页面中无 ---## 异常文本")

                    # 截图保存
                    screenshot_dir = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'outputs', 'test_screenshots'
                    )
                    os.makedirs(screenshot_dir, exist_ok=True)
                    timestamp = time.strftime('%Y%m%d_%H%M%S')
                    screenshot_path = os.path.join(screenshot_dir, f"markdown_fix_verify_{timestamp}.png")
                    page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"  📸 截图: {screenshot_path}")

                browser.close()
                return verify_result["passed"]
            else:
                logger.error("  ❌ 未获取到 task_id")
                browser.close()
                return False

        except Exception as e:
            logger.error(f"❌ 测试异常: {e}", exc_info=True)
            browser.close()
            return False


def main():
    parser = argparse.ArgumentParser(description="Markdown 排版修复验证测试")
    parser.add_argument("--headed", action="store_true", help="有头模式")
    parser.add_argument("--timeout", type=int, default=600, help="超时时间（秒）")
    args = parser.parse_args()

    passed = run_test(headed=args.headed, timeout=args.timeout)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
