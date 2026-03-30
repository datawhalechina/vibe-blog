#!/usr/bin/env python3
"""
Playwright E2E 测试：模拟用户在 vibe-blog 前端生成一篇 AI 话题博客
验证 71 号方案的 AI 话题自动增强搜索是否生效

前置条件：
  - 后端已启动: http://localhost:5001
  - 前端已启动: http://localhost:5173

用法：
  cd backend
  python tests/e2e_71_playwright.py
"""

import sys
import time
from playwright.sync_api import sync_playwright, expect


def run_e2e_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        print("=" * 60)
        print("🎬 E2E 测试：vibe-blog AI 话题博客生成")
        print("=" * 60)

        # ========== Step 1: 打开首页 ==========
        print("\n[Step 1] 打开首页...")
        page.goto("http://localhost:5173", wait_until="networkidle")
        page.wait_for_selector(".code-input-card", timeout=10000)
        print("  ✅ 首页加载完成")

        # ========== Step 2: 输入 AI 话题 ==========
        topic = "Claude MCP 协议详解：如何构建 AI Agent 工具链"
        print(f"\n[Step 2] 输入话题: {topic}")
        textarea = page.locator("textarea.code-input-textarea")
        textarea.click()
        textarea.fill(topic)
        print("  ✅ 话题已输入")

        # ========== Step 3: 展开高级选项，选择 mini 模式 ==========
        print("\n[Step 3] 展开高级选项...")
        advanced_btn = page.locator("button.code-action-btn:has-text('高级选项')")
        advanced_btn.click()
        page.wait_for_timeout(500)

        # 选择 mini 长度（最快生成）
        print("  选择 mini 长度...")
        length_select = page.locator("select").nth(1)  # 第二个 select 是长度
        length_select.select_option("mini")
        print("  ✅ 已选择 mini 模式")

        # ========== Step 4: 截图 - 生成前 ==========
        page.screenshot(path="/tmp/vibe-blog-e2e-before.png")
        print("\n[Step 4] 截图已保存: /tmp/vibe-blog-e2e-before.png")

        # ========== Step 5: 点击生成 ==========
        print("\n[Step 5] 点击生成按钮...")
        generate_btn = page.locator("button.code-generate-btn")
        generate_btn.click()

        # ========== Step 6: 等待进度抽屉出现 ==========
        print("\n[Step 6] 等待进度抽屉...")
        page.wait_for_selector(".progress-drawer", timeout=15000)
        print("  ✅ 进度抽屉已出现")

        # ========== Step 7: 监控日志输出 ==========
        print("\n[Step 7] 监控生成日志...")
        seen_logs = set()
        ai_boost_detected = False
        smart_search_detected = False
        max_wait = 900  # 最多等 15 分钟（串行模式下耗时较长）
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 检查日志
            log_items = page.locator(".progress-log-msg").all()
            for item in log_items:
                try:
                    text = item.inner_text(timeout=1000)
                    if text and text not in seen_logs:
                        seen_logs.add(text)
                        # 打印关键日志
                        if any(kw in text for kw in ['搜索', '智能', 'AI', '增强', '素材', '完成', '错误', 'Error']):
                            print(f"  📋 {text[:120]}")

                        # 检测 AI 增强搜索
                        if 'AI 话题增强' in text or 'AI boost' in text.lower():
                            ai_boost_detected = True
                            print(f"  🚀 检测到 AI 话题增强!")
                        if '智能搜索' in text or '智能知识源' in text:
                            smart_search_detected = True
                except Exception:
                    pass

            # 检查是否完成
            status = page.locator(".progress-status")
            if status.count() > 0:
                status_text = status.first.inner_text(timeout=2000)
                if "已完成" in status_text or "完成" in status_text:
                    print(f"\n  🎉 生成完成!")
                    break
                if "错误" in status_text or "失败" in status_text:
                    print(f"\n  ❌ 生成失败: {status_text}")
                    break

            page.wait_for_timeout(2000)

        # ========== Step 8: 截图 - 生成后 ==========
        page.screenshot(path="/tmp/vibe-blog-e2e-after.png")
        print(f"\n[Step 8] 截图已保存: /tmp/vibe-blog-e2e-after.png")

        # ========== Step 9: 等待跳转到博客详情页 ==========
        print("\n[Step 9] 等待跳转到博客详情页...")
        try:
            page.wait_for_url("**/blog/**", timeout=30000)
            final_url = page.url
            print(f"  ✅ 已跳转: {final_url}")

            # 截图博客详情
            page.wait_for_timeout(3000)
            page.screenshot(path="/tmp/vibe-blog-e2e-result.png", full_page=True)
            print(f"  📸 博客详情截图: /tmp/vibe-blog-e2e-result.png")
        except Exception as e:
            print(f"  ⚠️ 未跳转到详情页: {e}")

        # ========== 结果汇总 ==========
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 E2E 测试结果")
        print("=" * 60)
        print(f"  话题: {topic}")
        print(f"  耗时: {elapsed:.1f}s")
        print(f"  日志条数: {len(seen_logs)}")
        print(f"  智能搜索: {'✅' if smart_search_detected else '❌'}")
        print(f"  AI 增强: {'✅' if ai_boost_detected else '⚠️ 未在前端日志中检测到（可能仅在后端日志）'}")
        print("=" * 60)

        # 保持浏览器打开 10 秒供查看
        print("\n浏览器将在 10 秒后关闭...")
        page.wait_for_timeout(10000)

        browser.close()


if __name__ == "__main__":
    run_e2e_test()
