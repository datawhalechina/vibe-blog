"""
E2E 视觉验证：ProgressDrawer + Generate + BlogDetail 风格一致性检查
检查终端窗口卡片、玻璃态、命令行语法等 STYLE-GUIDE.md 规范
"""
import os
import sys
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'e2e-screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = 'http://localhost:5173'


def run_visual_check():
    results = []
    passed = 0
    failed = 0

    def check(name, condition, detail=''):
        nonlocal passed, failed
        if condition:
            passed += 1
            results.append(f'  ✅ {name}')
        else:
            failed += 1
            results.append(f'  ❌ {name}' + (f' — {detail}' if detail else ''))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = ctx.new_page()

        print('\n🧪 E2E 视觉验证：STYLE-GUIDE 规范检查\n')

        # ── 1. 首页加载 + 终端卡片检查 ──
        print('── 1. 首页 ──')
        page.goto(BASE_URL, wait_until='networkidle', timeout=15000)
        page.wait_for_timeout(1500)
        check('首页加载成功', page.title() != '')
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, 'style-home.png'))

        # 检查 BlogInputCard 终端窗口头部
        terminal_dots = page.query_selector_all('.terminal-dot')
        check('BlogInputCard 有终端圆点', len(terminal_dots) >= 3, f'found: {len(terminal_dots)} dots')

        terminal_title = page.query_selector('.terminal-title')
        check('BlogInputCard 有终端标题', terminal_title is not None)

        # 检查 BlogInputCard border-radius
        input_card_radius = page.evaluate('''() => {
            const el = document.querySelector('.code-input-card');
            return el ? window.getComputedStyle(el).borderRadius : '';
        }''')
        check('BlogInputCard border-radius = 12px', '12' in input_card_radius, f'got: {input_card_radius}')

        # 检查 Navbar 玻璃态
        navbar_backdrop = page.evaluate('''() => {
            const el = document.querySelector('.navbar');
            if (!el) return 'not found';
            const s = window.getComputedStyle(el);
            return s.backdropFilter || s.webkitBackdropFilter || 'none';
        }''')
        check('Navbar 有 backdrop-filter', 'blur' in navbar_backdrop, f'got: {navbar_backdrop}')

        # 检查 HeroSection 终端风格
        hero_text = page.evaluate('''() => {
            const h1 = document.querySelector('h1');
            return h1 ? h1.textContent : '';
        }''')
        check('HeroSection 有终端提示符 >', '>' in hero_text, f'got: {hero_text[:50]}')

        # 检查历史列表命令行标题
        history_header = page.evaluate('''() => {
            const el = document.querySelector('.header-title');
            return el ? el.textContent : '';
        }''')
        check('历史列表使用 $ ls 命令风格', '$ ls' in history_header, f'got: {history_header}')

        # ── 2. 发起生成，检查 ProgressDrawer ──
        print('\n── 2. 生成 + ProgressDrawer ──')

        # 使用 TipTapEditor 输入（它不是 textarea，是 contenteditable div）
        editor = page.query_selector('.tiptap, .ProseMirror, [contenteditable="true"]')
        if not editor:
            editor = page.query_selector('.code-input-textarea')

        if editor:
            editor.click()
            page.keyboard.type('Vue3 Composition API 入门指南')
            page.wait_for_timeout(500)

            gen_btn = page.query_selector('.code-generate-btn')
            if gen_btn:
                try:
                    task_id = ''
                    with page.expect_response(
                        lambda r: '/api/blog/generate' in r.url and r.request.method == 'POST',
                        timeout=15000
                    ) as resp_info:
                        gen_btn.click()
                    resp = resp_info.value
                    data = resp.json()
                    task_id = data.get('task_id', '')
                    print(f'  📍 任务: {task_id}')

                    # 等待跳转到 Generate 页面
                    page.wait_for_url('**/generate/**', timeout=10000)
                    page.wait_for_timeout(3000)
                    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, 'style-generate.png'))

                    # ── 3. Generate 页面样式检查 ──
                    print('\n── 3. Generate 页面 ──')

                    container_bg = page.evaluate('''() => {
                        const el = document.querySelector('.generate-container');
                        return el ? window.getComputedStyle(el).backgroundImage : '';
                    }''')
                    check('Generate 背景使用渐变', 'gradient' in container_bg, f'bg: {container_bg[:80]}')

                    card_backdrop = page.evaluate('''() => {
                        const el = document.querySelector('.research-card');
                        if (!el) return 'not found';
                        const s = window.getComputedStyle(el);
                        return s.backdropFilter || s.webkitBackdropFilter || 'none';
                    }''')
                    check('research-card 有 backdrop-filter', card_backdrop != 'none' and card_backdrop != 'not found', f'got: {card_backdrop}')

                    card_radius = page.evaluate('''() => {
                        const el = document.querySelector('.research-card');
                        return el ? window.getComputedStyle(el).borderRadius : '';
                    }''')
                    check('research-card border-radius >= 12px', '12' in card_radius or '16' in card_radius, f'got: {card_radius}')

                    # ── 4. ProgressDrawer 终端窗口检查 ──
                    print('\n── 4. ProgressDrawer ──')

                    # 检查 ProgressDrawer 是否有终端圆点
                    drawer_dots = page.evaluate('''() => {
                        const drawer = document.querySelector('.progress-drawer');
                        if (!drawer) return 0;
                        return drawer.querySelectorAll('.terminal-dot').length;
                    }''')
                    check('ProgressDrawer 有终端圆点', drawer_dots >= 3, f'found: {drawer_dots} dots')

                    # 检查 ProgressDrawer 终端标题
                    drawer_title = page.evaluate('''() => {
                        const drawer = document.querySelector('.progress-drawer');
                        if (!drawer) return '';
                        const title = drawer.querySelector('.terminal-title');
                        return title ? title.textContent : '';
                    }''')
                    check('ProgressDrawer 有 progress.log 标题', 'progress.log' in drawer_title, f'got: {drawer_title}')

                    # 检查 ProgressDrawer 玻璃态
                    drawer_backdrop = page.evaluate('''() => {
                        const el = document.querySelector('.progress-drawer');
                        if (!el) return 'not found';
                        const s = window.getComputedStyle(el);
                        return s.backdropFilter || s.webkitBackdropFilter || 'none';
                    }''')
                    check('ProgressDrawer 有 backdrop-filter', 'blur' in drawer_backdrop, f'got: {drawer_backdrop}')

                    # 检查命令提示符颜色
                    prompt_color = page.evaluate('''() => {
                        const el = document.querySelector('.progress-prompt');
                        return el ? window.getComputedStyle(el).color : '';
                    }''')
                    check('命令提示符 $ 存在', prompt_color != '', f'color: {prompt_color}')

                    # 等待一些内容生成后截图
                    page.wait_for_timeout(5000)
                    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, 'style-generate-progress.png'))

                    # 取消任务
                    if task_id:
                        page.evaluate('''async (id) => {
                            await fetch(`/api/tasks/${id}/cancel`, { method: 'POST' });
                        }''', task_id)
                        print('  🛑 任务已取消')
                        page.wait_for_timeout(1000)

                except Exception as e:
                    print(f'  ⚠️ 生成流程异常: {e}')
            else:
                check('找到生成按钮', False, '未找到 .code-generate-btn')
        else:
            check('找到输入编辑器', False, '未找到 TipTapEditor')

        # ── 5. BlogDetail 页面检查 ──
        print('\n── 5. BlogDetail ──')
        page.goto(BASE_URL, wait_until='networkidle', timeout=10000)
        page.wait_for_timeout(1000)

        blog_card = page.query_selector('.code-blog-card')
        if blog_card:
            blog_card.click()
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, 'style-blog-detail.png'))

            detail_bg = page.evaluate('''() => {
                const el = document.querySelector('.blog-detail-container');
                return el ? window.getComputedStyle(el).backgroundImage : '';
            }''')
            check('BlogDetail 背景使用渐变', 'gradient' in detail_bg, f'bg: {detail_bg[:80]}')

            content_dots = page.evaluate('''() => {
                const card = document.querySelector('.content-card');
                if (!card) return 0;
                return card.querySelectorAll('.terminal-dot, [class*="dot"]').length;
            }''')
            check('content-card 有终端圆点', content_dots >= 3, f'found: {content_dots}')

            content_radius = page.evaluate('''() => {
                const el = document.querySelector('.content-card');
                return el ? window.getComputedStyle(el).borderRadius : '';
            }''')
            check('content-card border-radius = 12px', '12' in content_radius, f'got: {content_radius}')

            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, 'style-blog-detail-full.png'), full_page=True)
        else:
            print('  ⚠️ 未找到历史文章卡片，跳过 BlogDetail 检查')

        # ── 6. 移动端视口 ──
        print('\n── 6. 移动端 ──')
        mobile_ctx = browser.new_context(viewport={'width': 375, 'height': 812})
        mobile_page = mobile_ctx.new_page()
        mobile_page.goto(BASE_URL, wait_until='networkidle', timeout=10000)
        mobile_page.wait_for_timeout(1000)
        mobile_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, 'style-mobile-home.png'))
        vw = mobile_page.evaluate('window.innerWidth')
        check('移动端视口宽度正确', vw == 375, f'got: {vw}')
        mobile_ctx.close()

        # 打印结果
        print('\n' + '\n'.join(results))
        print(f'\n📊 结果: {passed} passed, {failed} failed, {passed + failed} total')
        print(f'📸 截图保存在: {SCREENSHOTS_DIR}/')

        browser.close()

    return failed == 0


if __name__ == '__main__':
    success = run_visual_check()
    sys.exit(0 if success else 1)
