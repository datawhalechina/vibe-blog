"""
AionUi 迁移 — 完整端到端验证
实际生成一篇博客，在生成过程中验证所有 6 个新特性
"""
import sys
import os
import time

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from playwright.sync_api import sync_playwright

import urllib.request
import json

FRONTEND = "http://localhost:5173"
BACKEND = "http://localhost:5001"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "outputs", "e2e_screenshots", "full_e2e")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

results = []
console_errors = []


def record(feature, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((feature, name, status, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def shot(page, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path


def main():
    print("=" * 60)
    print("AionUi 完整端到端验证 — 生成博客 + 验证全部特性")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        try:
            run_full_e2e(page)
        except Exception as e:
            print(f"\n!!! 异常: {e}")
            shot(page, "99_error")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

    # 汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    passed = sum(1 for *_, s, _ in results if s == "PASS")
    failed = sum(1 for *_, s, _ in results if s == "FAIL")
    current_feature = ""
    for feature, name, status, detail in results:
        if feature != current_feature:
            current_feature = feature
            print(f"\n  [{feature}]")
        icon = "✅" if status == "PASS" else "❌"
        print(f"    {icon} {name}" + (f" — {detail}" if detail else ""))
    print(f"\n总计: {passed} 通过, {failed} 失败, 共 {len(results)} 项")

    if console_errors:
        errs = [e for e in console_errors if 'favicon' not in e.lower()]
        if errs:
            print(f"\n⚠️  控制台错误 ({len(errs)}):")
            for e in errs[:5]:
                print(f"  - {e[:200]}")

    print(f"\n截图: {SCREENSHOT_DIR}")
    sys.exit(1 if failed > 0 else 0)


def run_full_e2e(page):
    # ══════════════════════════════════════════
    # Step 1: 首页 — 验证拖拽上传 + 粘贴
    # ══════════════════════════════════════════
    print("\n── Step 1: 首页加载 + 拖拽上传验证 ──")
    page.goto(FRONTEND)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    shot(page, "01_home_loaded")

    # 115.03 拖拽上传
    card = page.locator(".code-input-card")
    record("115.03", "BlogInputCard 渲染", card.count() > 0)

    page.evaluate("""() => {
        const card = document.querySelector('.code-input-card');
        if (!card) return;
        const dt = new DataTransfer();
        dt.items.add(new File(['test'], 'test.pdf', { type: 'application/pdf' }));
        card.dispatchEvent(new DragEvent('dragenter', { bubbles: true, dataTransfer: dt }));
    }""")
    page.wait_for_timeout(500)
    overlay = page.locator(".drag-overlay")
    record("115.03", "拖拽 overlay 触发", overlay.count() > 0)
    shot(page, "02_drag_overlay")

    # 取消拖拽
    page.evaluate("""() => {
        const card = document.querySelector('.code-input-card');
        if (!card) return;
        card.dispatchEvent(new DragEvent('dragleave', { bubbles: true }));
    }""")
    page.wait_for_timeout(300)

    # ══════════════════════════════════════════
    # Step 2: 输入主题并生成博客
    # ══════════════════════════════════════════
    print("\n── Step 2: 输入主题 + 触发生成 ──")

    # TipTap 编辑器输入
    tiptap = page.locator(".tiptap-content .tiptap")
    tiptap.click()
    page.wait_for_timeout(300)
    # 使用 KaTeX 相关主题来验证数学公式渲染
    page.keyboard.type("Python 装饰器入门教程", delay=30)
    page.wait_for_timeout(500)
    shot(page, "03_topic_entered")

    # 点击生成按钮
    gen_btn = page.locator(".code-generate-btn")
    record("首页", "生成按钮可点击", gen_btn.count() > 0 and gen_btn.is_enabled())
    gen_btn.click()
    print("  → 已点击生成按钮，等待跳转到 Generate 页面...")

    # 等待路由跳转到 /generate/{task_id}
    page.wait_for_url("**/generate/**", timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    current_url = page.url
    record("首页", "跳转到 Generate 页面", "/generate/" in current_url, f"url={current_url}")
    shot(page, "04_generate_page")

    # ══════════════════════════════════════════
    # Step 3: Generate 页面 — 验证分割面板 + 打字动画 + Token 圆环
    # ══════════════════════════════════════════
    print("\n── Step 3: Generate 页面特性验证 ──")

    # 115.05 分割面板
    split_handle = page.locator(".split-handle")
    record("115.05", "split-handle 分割线存在", split_handle.count() > 0)

    left = page.locator(".generate-left")
    left_width = page.evaluate("() => document.querySelector('.generate-left')?.style.width || ''")
    record("115.05", "左栏动态宽度", "%" in left_width, f"width={left_width}")

    # 115.05 分割面板拖拽测试
    if split_handle.count() > 0:
        box = split_handle.bounding_box()
        if box:
            # 拖拽分割线向右移动 100px
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + 100, box["y"] + box["height"] / 2, steps=5)
            page.mouse.up()
            page.wait_for_timeout(300)
            new_width = page.evaluate("() => document.querySelector('.generate-left')?.style.width || ''")
            record("115.05", "分割线拖拽生效", new_width != left_width,
                   f"拖拽前={left_width}, 拖拽后={new_width}")
            shot(page, "05_split_dragged")

    # 115.01a ProgressDrawer + 智能滚动
    drawer = page.locator(".progress-drawer")
    record("115.01a", "ProgressDrawer 渲染", drawer.count() > 0)

    # card-toolbar（TokenUsageRing 的容器）
    toolbar = page.locator(".card-toolbar")
    record("115.01b", "card-toolbar 工具栏存在", toolbar.count() > 0)

    # ══════════════════════════════════════════
    # Step 4: 等待生成过程，观察进度
    # ══════════════════════════════════════════
    print("\n── Step 4: 等待生成过程（最多 300s）──")

    max_wait = 300  # 最多等 5 分钟
    check_interval = 5
    elapsed = 0
    has_progress = False
    has_preview = False
    has_token_ring = False
    generation_complete = False

    while elapsed < max_wait:
        page.wait_for_timeout(check_interval * 1000)
        elapsed += check_interval

        # 检查进度日志
        log_count = page.locator(".progress-log-item, .log-item, [class*='log-item']").count()
        if log_count > 0 and not has_progress:
            has_progress = True
            print(f"  → {elapsed}s: 进度日志出现 ({log_count} 条)")
            shot(page, f"06_progress_{elapsed}s")

        # 检查大纲确认按钮（仅在 interactive 模式下出现）
        confirm_btn = page.locator("button:has-text('开始写作')")
        if confirm_btn.count() > 0:
            confirm_btn.first.click()
            print(f"  → {elapsed}s: 已点击确认大纲按钮")
            page.wait_for_timeout(2000)

        # 检查预览内容（使用正确的 #preview-content 选择器）
        preview_len = page.evaluate("""() => {
            const el = document.querySelector('#preview-content') || document.querySelector('.preview-panel');
            return el ? (el.textContent || '').trim().length : 0;
        }""")
        if preview_len > 50 and not has_preview:
            has_preview = True
            print(f"  → {elapsed}s: 预览内容出现 ({preview_len} 字符)")
            shot(page, f"08_preview_{elapsed}s")

        # 检查 TokenUsageRing
        token_ring = page.locator(".token-usage-ring")
        if token_ring.count() > 0 and not has_token_ring:
            has_token_ring = True
            print(f"  → {elapsed}s: TokenUsageRing 出现")
            shot(page, f"09_token_ring_{elapsed}s")

        # 检查是否完成 — .view-article-btn 出现
        view_btn = page.locator(".view-article-btn")
        if view_btn.count() > 0:
            generation_complete = True
            print(f"  → {elapsed}s: 生成完成！（前端检测）")
            shot(page, "10_generation_complete")
            break

        # 后端 API 轮询 — SSE 可能断开，但后端任务已完成
        if elapsed % 15 == 0 and elapsed > 0:
            task_id = current_url.split("/generate/")[-1].split("?")[0] if "/generate/" in current_url else ""
            if task_id:
                try:
                    req = urllib.request.urlopen(f"{BACKEND}/api/tasks/{task_id}", timeout=3)
                    data = json.loads(req.read())
                    task_status = data.get("task", {}).get("status", "")
                    if task_status in ("completed", "done", "success"):
                        generation_complete = True
                        print(f"  → {elapsed}s: 生成完成！（后端 API 检测, status={task_status}）")
                        shot(page, "10_generation_complete_api")
                        # 刷新页面让前端重新获取状态
                        page.reload()
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(2000)
                        break
                    elif task_status in ("failed", "error"):
                        print(f"  → {elapsed}s: 后端任务失败 (status={task_status})")
                        break
                except Exception:
                    pass

        # 每 30 秒截图 + 状态报告
        if elapsed % 30 == 0:
            shot(page, f"progress_{elapsed}s")
            status = page.evaluate("""() => {
                const badge = document.querySelector('.status-badge');
                return badge ? badge.textContent?.trim() : '未知';
            }""")
            print(f"  → {elapsed}s: 等待中... 状态={status}")

    record("生成流程", "进度日志出现", has_progress)
    record("生成流程", "预览内容出现", has_preview)
    record("115.01b", "TokenUsageRing 在生成中出现", has_token_ring,
           "依赖后端 SSE 返回 token_usage（前端组件已集成，v-if 条件控制显示）" if not has_token_ring else "")
    record("生成流程", "生成完成", generation_complete,
           f"耗时约 {elapsed}s" if generation_complete else f"超时 {max_wait}s")

    # ══════════════════════════════════════════
    # Step 5: 生成完成后 — 验证博客详情页 + 字体控制
    # ══════════════════════════════════════════
    if generation_complete:
        print("\n── Step 5: 博客详情页 + 字体控制 ──")

        # 尝试通过 view-article-btn 进入详情页
        view_btn = page.locator(".view-article-btn")
        blog_loaded = False
        if view_btn.count() > 0:
            view_btn.first.click()
            try:
                page.wait_for_url("**/blog/**", timeout=10000)
                blog_loaded = True
            except Exception:
                pass

        # 备选：从 URL 中提取 task_id 作为 blog_id 直接导航
        if not blog_loaded:
            task_id = current_url.split("/generate/")[-1].split("?")[0] if "/generate/" in current_url else ""
            if task_id:
                page.goto(f"{FRONTEND}/blog/{task_id}")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                # 检查是否成功加载
                blog_loaded = page.locator(".blog-detail, .blog-content, [class*='blog-detail']").count() > 0

        if blog_loaded:
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            shot(page, "11_blog_detail")

            # 115.05 FontSizeControl
            font_ctrl = page.locator(".font-size-control")
            record("115.05", "FontSizeControl 在详情页渲染", font_ctrl.count() > 0)

            if font_ctrl.count() > 0:
                # 点击放大按钮
                plus_btn = page.locator(".font-size-control__btn").last
                if plus_btn.count() > 0:
                    plus_btn.click()
                    page.wait_for_timeout(300)
                    scale = page.evaluate("""() =>
                        getComputedStyle(document.documentElement).getPropertyValue('--font-scale').trim()
                    """)
                    record("115.05", "字体放大生效", scale != "1", f"--font-scale={scale}")
                    shot(page, "12_font_scaled")

            # 115.02 KaTeX — 博客内容中的数学公式（取决于内容）
            has_katex = page.locator(".katex").count() > 0
            if has_katex:
                record("115.02", "博客内容中 KaTeX 渲染", True)
    else:
        print("\n── Step 5: 生成未完成，尝试用已有博客验证详情页特性 ──")
        # 即使本次生成未完成，也可以用已有博客验证 FontSizeControl 和 KaTeX
        try:
            req = urllib.request.urlopen(f"{BACKEND}/api/blogs/with-book-info", timeout=5)
            data = json.loads(req.read())
            blogs = data.get("blogs", data) if isinstance(data, dict) else data
            if blogs:
                last_blog_id = blogs[-1].get("id", "")
                if last_blog_id:
                    print(f"  → 使用已有博客 {last_blog_id} 验证详情页特性")
                    page.goto(f"{FRONTEND}/blog/{last_blog_id}")
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                    shot(page, "11_blog_detail_fallback")

                    font_ctrl = page.locator(".font-size-control")
                    record("115.05", "FontSizeControl 在详情页渲染", font_ctrl.count() > 0)
                    if font_ctrl.count() > 0:
                        plus_btn = page.locator(".font-size-control__btn").last
                        if plus_btn.count() > 0:
                            plus_btn.click()
                            page.wait_for_timeout(300)
                            scale = page.evaluate("""() =>
                                getComputedStyle(document.documentElement).getPropertyValue('--font-scale').trim()
                            """)
                            record("115.05", "字体放大生效", scale != "1", f"--font-scale={scale}")
                            shot(page, "12_font_scaled_fallback")

                    has_katex = page.locator(".katex").count() > 0
                    record("115.02", "博客内容中 KaTeX 渲染", has_katex,
                           "取决于博客内容是否包含数学公式")
        except Exception as e:
            print(f"  → 无法获取已有博客: {e}")

    # ══════════════════════════════════════════
    # Step 6: Cron 管理页面
    # ══════════════════════════════════════════
    print("\n── Step 6: Cron 管理页面 ──")
    page.goto(f"{FRONTEND}/cron")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    record("115.04", "CronManager 页面加载", page.locator(".cron-manager").count() > 0)
    record("115.04", "统计芯片", page.locator(".stat-chip").count() > 0,
           f"数量={page.locator('.stat-chip').count()}")
    record("115.04", "页面标题 '$ crontab'",
           page.locator(".page-title").count() > 0)
    shot(page, "13_cron_page")

    # ══════════════════════════════════════════
    # Step 7: KaTeX 渲染验证（独立测试）
    # ══════════════════════════════════════════
    print("\n── Step 7: KaTeX 数学公式渲染验证 ──")
    page.goto(FRONTEND)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # 使用 useMarkdownRenderer 渲染含数学公式的 markdown，注入到页面验证
    katex_result = page.evaluate("""async () => {
        try {
            const mod = await import('/src/composables/useMarkdownRenderer.ts');
            const { renderMarkdown } = mod.useMarkdownRenderer();
            const html = renderMarkdown('公式测试: $E=mc^2$ 和 $$\\\\int_0^1 x^2 dx$$');
            // 注入到页面中检查渲染结果
            const div = document.createElement('div');
            div.id = 'katex-test';
            div.innerHTML = html;
            document.body.appendChild(div);
            const hasKatex = div.querySelectorAll('.katex').length;
            const hasHtml = div.querySelector('.katex-html') !== null;
            document.body.removeChild(div);
            return { hasKatex, hasHtml, htmlSnippet: html.substring(0, 200) };
        } catch (e) {
            return { error: e.message };
        }
    }""")
    if isinstance(katex_result, dict) and 'error' not in katex_result:
        record("115.02", "KaTeX 公式渲染（inline + block）",
               katex_result.get("hasKatex", 0) >= 2,
               f"找到 {katex_result.get('hasKatex', 0)} 个 .katex 元素")
        record("115.02", "KaTeX HTML 输出",
               katex_result.get("hasHtml", False))
    else:
        record("115.02", "KaTeX 渲染", False,
               katex_result.get("error", "未知错误") if isinstance(katex_result, dict) else str(katex_result))


if __name__ == "__main__":
    main()
